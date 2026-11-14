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
    if bool(cfg.get("NOMI_VOICE_COMMANDS")) != (profile == "commands"):
        raise ValueError("Wrong command recognition profile")
    data = (build / "srmodels" / "srmodels.bin").read_bytes()
    # Parse every model record rather than assuming directory/packing order.
    count = struct.unpack_from("<I", data)[0]
    if count > 16: raise ValueError("Invalid model count")
    names = []; cursor = 4
    for _ in range(count):
        if cursor+36 > len(data): raise ValueError("Truncated model header")
        names.append(data[cursor:cursor+32].split(b"\0")[0].decode("ascii"))
        files = struct.unpack_from("<I", data, cursor+32)[0]
        cursor += 36+files*40
        if cursor > len(data): raise ValueError("Truncated model file table")
    expected = {"audio": [], "benchmark": ["wn9_xiaoaitongxue"], "commands": ["mn7_cn", "fst"]}[profile]
    if sorted(names) != sorted(expected): raise ValueError(f"Wrong models: {names}")
    if len(data) > 0x400000: raise ValueError("Model partition overflow")
    args = json.loads((build / "flasher_args.json").read_text(encoding="utf-8"))
    offsets = {int(k, 0) for k in args["flash_files"]}
    if offsets != {0, 0x8000, 0x10000, 0x410000}:
        raise ValueError(f"Unexpected flash layout: {offsets}")
    nm = shutil.which("xtensa-esp32s3-elf-nm")
    if not nm:
        raise ValueError("Xtensa nm is required to audit the linked ELF")
    symbols = subprocess.check_output([nm, "--defined-only", str(build / "desktop_nomi_h2.elf")], text=True)
    for forbidden in ("esp_wifi_init", "esp_http_client_init", "esp_tls_conn_new", "esp_tts_create"):
        if forbidden in symbols:
            raise ValueError(f"Out-of-scope runtime linked: {forbidden}")
    if profile != "commands" and "esp_mn_handle_from_name" in symbols:
        raise ValueError("Command recognizer linked into diagnostic-only profile")
    if profile == "commands" and "esp_mn_handle_from_name" not in symbols:
        raise ValueError("Command recognizer missing")
    print(f"Validated {profile}: models={names}; no Wi-Fi/HTTP/TLS/TTS entry points linked")
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
    for name in ("HARDWARE_H2.md", "HARDWARE_H1.md", "HARDWARE_VOICE.md"):
        files["docs/" + name] = ROOT.parent / "docs" / name
    built_config = json.loads((build / "config/sdkconfig.json").read_text(encoding="utf-8"))
    description = {
        "board": "Waveshare ESP32-S3-Touch-LCD-1.85B", "idf": "5.5.4", "profile": profile,
        "target_phrase": "小米同学", "dedicated_wakenet_model_available": False,
        "active_model": "mn7_cn" if profile == "commands" else "wn9_xiaoaitongxue" if profile == "benchmark" else None,
        "activation_method": "continuous_multinet_command" if profile == "commands" else None,
        "configured_activation_phrase": built_config.get("NOMI_VOICE_WAKE_LABEL") if profile == "commands" else None,
        "configured_activation_pinyin": built_config.get("NOMI_VOICE_WAKE_PINYIN") if profile == "commands" else None,
        "firmware_version": json.loads((build / "project_description.json").read_text(encoding="utf-8"))["project_version"],
        "voice_hardware_verified": False,
        "active_phrase": built_config.get("NOMI_VOICE_WAKE_LABEL") if profile == "commands" else "小爱同学 (BENCHMARK ONLY)" if profile == "benchmark" else None,
        "source_commit": source_git("rev-parse", "HEAD"),
        "source_dirty": bool(source_git("status", "--porcelain")),
        "sha256": {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in files.items()},
        "flash_files": args["flash_files"],
    }
    # The supplied response file preserves exact offsets; no full-chip erase/merged image.
    readme = f'''Desktop-NOMI H2 / {profile}
Board: Waveshare ESP32-S3-Touch-LCD-1.85B ONLY
Dedicated Xiaomi Tongxue WakeNet model: UNAVAILABLE
Commands profile uses MultiNet7 with configurable activation phrase 小米同学.
Read docs/HARDWARE_VOICE.md for phrases and acceptance tests.
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
    parser.add_argument("--profile", choices=("audio", "benchmark", "commands"), default="audio")
    parser.add_argument("--package", action="store_true")
    parser.add_argument("--skip-prepare", action="store_true")
    options = parser.parse_args()
    if not options.skip_prepare:
        subprocess.run([sys.executable, str(ROOT / "scripts/prepare.py")], check=True)
    idf = pathlib.Path(os.environ["IDF_PATH"]) / "tools/idf.py"
    build = ROOT / ("build-" + options.profile)
    config = ROOT / ("sdkconfig." + options.profile + ".local")
    defaults = str(ROOT / "sdkconfig.defaults")
    if options.profile != "audio":
        defaults += ";" + str(ROOT / ("sdkconfig." + options.profile))
    subprocess.run([sys.executable, str(idf), "-B", str(build), "-D", f"SDKCONFIG={config}",
                    "-D", f"SDKCONFIG_DEFAULTS={defaults}", "build", "size"], cwd=ROOT, check=True)
    args = validate(build, options.profile)
    if options.package:
        package(build, options.profile, config, args)


if __name__ == "__main__":
    main()
