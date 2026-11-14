"""Build isolated H2 profiles and package verified files. Never flashes a device."""
import argparse
import hashlib
import json
import os
import pathlib
import shutil
import struct
import subprocess
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]


def source_git(*args):
    # Actions containers may use a different UID from the checkout owner.
    # Trust only this known repository, for this single Git invocation.
    return subprocess.check_output(
        ["git", "-c", f"safe.directory={ROOT.parent.resolve()}", *args], cwd=ROOT, text=True
    ).strip()


def validate(build, profile):
    config = (build / "config" / "sdkconfig.json").read_text(encoding="utf-8")
    cfg = json.loads(config)
    if cfg.get("IDF_TARGET") != "esp32s3" or not cfg.get("SPIRAM_MODE_OCT"):
        raise ValueError("Unexpected target or PSRAM mode")
    if bool(cfg.get("NOMI_WAKE_BENCHMARK")) != (profile == "benchmark"):
        raise ValueError("Wrong profile in existing build directory")
    data = (build / "srmodels" / "srmodels.bin").read_bytes()
    count = struct.unpack_from("<I", data)[0]
    if count != (1 if profile == "benchmark" else 0):
        raise ValueError("Unexpected model count: audio must have none; benchmark exactly one")
    if count and data[4:36].split(b"\0")[0] != b"wn9_xiaoaitongxue":
        raise ValueError("Model identity mismatch")
    args = json.loads((build / "flasher_args.json").read_text(encoding="utf-8"))
    offsets = {int(k, 0) for k in args["flash_files"]}
    if offsets != {0, 0x8000, 0x10000, 0x410000}:
        raise ValueError(f"Unexpected flash layout: {offsets}")
    nm = shutil.which("xtensa-esp32s3-elf-nm")
    if not nm:
        raise ValueError("Xtensa nm is required to audit the linked ELF")
    symbols = subprocess.check_output([nm, "--defined-only", str(build / "desktop_nomi_h2.elf")], text=True)
    for forbidden in ("esp_wifi_init", "esp_http_client_init", "esp_tls_conn_new", "esp_mn_handle_from_name", "esp_tts_create"):
        if forbidden in symbols:
            raise ValueError(f"Out-of-scope runtime linked: {forbidden}")
    print(f"Validated {profile}: model_count={count}; no Wi-Fi/HTTP/TLS/ASR/TTS entry points linked")
    return args


def package(build, profile, config, args):
    output = ROOT / "dist" / f"desktop-nomi-h2-{profile}.zip"
    output.parent.mkdir(exist_ok=True)
    files = {name: build / name for name in args["flash_files"].values()}
    for name in ("flash_args", "flasher_args.json", "desktop_nomi_h2.elf", "desktop_nomi_h2.map"):
        files[name] = build / name
    files["sdkconfig"] = config
    files["dependencies.lock.json"] = ROOT / "dependencies.lock.json"
    for name, path in {
        "ESP-SR.txt": ".deps/esp-sr/LICENSE", "ESP-DSP.txt": ".deps/espressif__esp-dsp/LICENSE",
        "esp_codec_dev.txt": ".deps/esp-adf/components/esp_codec_dev/LICENSE",
        "LVGL.txt": "components/lvgl/LICENCE.txt", "LVGL-COPYRIGHTS.md": "components/lvgl/COPYRIGHTS.md",
        "Waveshare.txt": "components/nomi_panel/LICENSE", "panel-NOTICE.md": "components/nomi_panel/NOTICE.md",
        "H2-NOTICE.md": "components/nomi_audio/NOTICE.md",
    }.items():
        files["licenses/" + name] = ROOT / path
    for name in ("HARDWARE_H2.md", "HARDWARE_H1.md"):
        files["docs/" + name] = ROOT.parent / "docs" / name
    description = {
        "board": "Waveshare ESP32-S3-Touch-LCD-1.85B", "idf": "5.5.4", "profile": profile,
        "target_phrase": "小米同学", "target_model_available": False,
        "active_model": "wn9_xiaoaitongxue" if profile == "benchmark" else None,
        "active_phrase": "小爱同学 (BENCHMARK ONLY)" if profile == "benchmark" else None,
        "source_commit": source_git("rev-parse", "HEAD"),
        "source_dirty": bool(source_git("status", "--porcelain")),
        "sha256": {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in files.items()},
        "flash_files": args["flash_files"],
    }
    # The supplied response file preserves exact offsets; no full-chip erase/merged image.
    readme = f'''Desktop-NOMI H2 / {profile}
Board: Waveshare ESP32-S3-Touch-LCD-1.85B ONLY
Xiaomi Tongxue (小米同学) model: UNAVAILABLE
Benchmark phrase, if selected: Xiaoai Tongxue (小爱同学), NOT Xiaomi Tongxue
Read docs/HARDWARE_H2.md and verify/back up your own board first.
Windows ESP-IDF terminal, from THIS extracted folder:
  python -m esptool --chip esp32s3 --port COM3 --baud 460800 write_flash "@flash_args"
Replace COM3 with your actual port. No erase_flash is needed.
Terminal:
  python -m serial.tools.miniterm COM3 115200 --eol CRLF
Commands: status / demo / wake off / wake on / wake reinit / wake status
See manifest.json for offsets, SHA256 and model identity.
'''
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, path in files.items():
            archive.write(path, name)
        archive.writestr("manifest.json", json.dumps(description, ensure_ascii=False, indent=2) + "\n")
        archive.writestr("READ-ME-FIRST.txt", readme)
    print(output)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("audio", "benchmark"), default="audio")
    parser.add_argument("--package", action="store_true")
    parser.add_argument("--skip-prepare", action="store_true")
    options = parser.parse_args()
    if not options.skip_prepare:
        subprocess.run([sys.executable, str(ROOT / "scripts/prepare.py")], check=True)
    idf = pathlib.Path(os.environ["IDF_PATH"]) / "tools/idf.py"
    build = ROOT / ("build-" + options.profile)
    config = ROOT / ("sdkconfig." + options.profile + ".local")
    defaults = str(ROOT / "sdkconfig.defaults")
    if options.profile == "benchmark":
        defaults += ";" + str(ROOT / "sdkconfig.benchmark")
    subprocess.run([sys.executable, str(idf), "-B", str(build), "-D", f"SDKCONFIG={config}",
                    "-D", f"SDKCONFIG_DEFAULTS={defaults}", "build", "size"], cwd=ROOT, check=True)
    args = validate(build, options.profile)
    if options.package:
        package(build, options.profile, config, args)


if __name__ == "__main__":
    main()
