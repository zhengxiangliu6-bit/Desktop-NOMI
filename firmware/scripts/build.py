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
    if bool(cfg.get("NOMI_USB_ASR")) != (profile == "usb_asr"):
        raise ValueError("Wrong USB ASR profile")
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
    expected = {"audio": [], "usb_asr": [], "benchmark": ["wn9_xiaoaitongxue"], "commands": ["mn7_cn", "fst"]}[profile]
    if sorted(names) != sorted(expected): raise ValueError(f"Wrong models: {names}")
    if len(data) > 0x400000: raise ValueError("Model partition overflow")
    if profile in ("usb_asr","commands"):
        asset = ROOT / "components/nomi_audio/assets/okay.pcm"
        meta = json.loads(asset.with_suffix(".json").read_text(encoding="utf-8"))
        pcm = asset.read_bytes()
        if meta.get("text") != "好的" or meta.get("sample_rate") != 16000 or meta.get("channels") != 1 or meta.get("format") != "s16le" or meta.get("bytes") != len(pcm) or meta.get("samples") != len(pcm)//2 or not 0 < len(pcm) <= 96000 or len(pcm)%2 or hashlib.sha256(pcm).hexdigest() != meta["sha256"]:
            raise ValueError("Fixed reply asset format/hash mismatch")
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
    files["expressions.json"] = ROOT.parent / "shared/expressions.json"
    files["dependencies.lock.json"] = ROOT / "dependencies.lock.json"
    for name, path in {
        "ESP-SR.txt": ".deps/esp-sr/LICENSE", "ESP-DSP.txt": ".deps/espressif__esp-dsp/LICENSE",
        "esp_codec_dev.txt": ".deps/esp-adf/components/esp_codec_dev/LICENSE",
        "LVGL.txt": "components/lvgl/LICENCE.txt", "LVGL-COPYRIGHTS.md": "components/lvgl/COPYRIGHTS.md",
        "Waveshare.txt": "components/nomi_panel/LICENSE", "panel-NOTICE.md": "components/nomi_panel/NOTICE.md",
        "H2-NOTICE.md": "components/nomi_audio/NOTICE.md",
    }.items():
        files["licenses/" + name] = ROOT / path
    for name in ("HARDWARE_H2.md", "HARDWARE_H1.md", "HARDWARE_VOICE.md", "USB_CHINESE_TRANSCRIPTION.md", "PC_VOICE_CONTROL.md", "SPOKEN_OKAY.md", "EXPRESSION_GALLERY.md", "VOICE_NEXT_PLAN.md", "OFFLINE_COMMAND_REPLY.md"):
        files["docs/" + name] = ROOT.parent / "docs" / name
    if profile in ("usb_asr","commands"):
        # Export the exact embedded PCM as a listenable WAV, without a second source asset.
        import wave
        preview=build / "okay-preview.wav"
        with wave.open(str(preview),"wb") as wav_output:
            wav_output.setnchannels(1); wav_output.setsampwidth(2); wav_output.setframerate(16000)
            wav_output.writeframes((ROOT / "components/nomi_audio/assets/okay.pcm").read_bytes())
        files["okay-preview.wav"]=preview
        files["assets/okay.json"] = ROOT / "components/nomi_audio/assets/okay.json"
        files["licenses/OKAY-ASSET.md"] = ROOT / "components/nomi_audio/assets/NOTICE.md"
        files["licenses/MeloTTS.txt"] = ROOT / "components/nomi_audio/assets/MeloTTS-LICENSE.txt"
    if profile == "usb_asr":
        host = ROOT.parent / "tools/usb_asr"
        files["pc/VOICE_CONTROL_GUIDE.md"] = ROOT.parent / "docs/PC_VOICE_CONTROL.md"
        files["pc/EXPRESSION_GUIDE.md"] = ROOT.parent / "docs/EXPRESSION_GALLERY.md"
        files["pc/SPOKEN_OKAY_GUIDE.md"] = ROOT.parent / "docs/SPOKEN_OKAY.md"
        for path in host.iterdir():
            if path.is_file() and path.suffix in (".py", ".cmd", ".txt", ".json", ".md"):
                files["pc/" + path.name] = path
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
        "asr_location": "Windows local CPU" if profile == "usb_asr" else None,
        "microphone_starts": "explicit host request with 2s heartbeat" if profile == "usb_asr" else "boot",
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
    if profile == "commands":
        readme += "\nOFFLINE 0.6.0: 14 local face commands + fixed reply; no PC application needed.\nRead docs/OFFLINE_COMMAND_REPLY.md. WAV replacement needs rebuild + reflash.\n"
    if profile == "usb_asr":
        readme = """Desktop-NOMI 14 expression gallery + fixed spoken OK / firmware 0.6.0
Board: Waveshare ESP32-S3-Touch-LCD-1.85B ONLY
Device captures audio. ASR runs LOCALLY on Windows.
0.6.0 shares the fixed player with offline commands; PC0.5.0 remains compatible; playback guard temporarily suppresses microphone ASR.
Read docs/EXPRESSION_GALLERY.md. Test faces with start_control.cmd COM3 --silent-replies first.
Read docs/SPOKEN_OKAY.md. Keep your installed pc/.venv and models when merging pc files.
Read docs/USB_CHINESE_TRANSCRIPTION.md before use.
Flash all files with the supplied flash_args, no full-chip erase:
  python -m esptool --chip esp32s3 --port COM3 --baud 460800 write_flash "@flash_args"
Close miniterm/other COM3 apps. In an ESP-IDF terminal, first run:
  pc\\setup.cmd
Then:
  pc\\start_control.cmd COM3
For an existing installation: merge pc files into your original pc folder, keep .venv and models.
No setup/model download is needed again. First-time setup downloads the pinned ~21MB model.
Runtime does not upload audio or save recordings/transcripts.
Press Enter in the app to start the board microphone; Ctrl+C stops it.
Do not use a separate miniterm while the app owns COM3.
See manifest.json for file hashes and source revision.
"""
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, path in files.items():
            archive.write(path, name)
        archive.writestr("manifest.json", json.dumps(description, ensure_ascii=False, indent=2) + "\n")
        archive.writestr("READ-ME-FIRST.txt", readme)
    print(output)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("audio", "benchmark", "commands", "usb_asr"), default="audio")
    parser.add_argument("--package", action="store_true")
    parser.add_argument("--skip-prepare", action="store_true")
    options = parser.parse_args()
    if not options.skip_prepare:
        subprocess.run([sys.executable, str(ROOT / "scripts/prepare.py")], check=True)
    subprocess.run([sys.executable,str(ROOT / "scripts/generate_faces.py"),"--check"],check=True)
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
