"""Reject wrong model/profile/offsets/network linkage before offering a flash bundle."""
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("nomi_build", Path(__file__).parents[1] / "scripts/build.py")
build_tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_tool)


class BuildAuditTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "config").mkdir()
        (self.root / "srmodels").mkdir()
        self.config = {"IDF_TARGET": "esp32s3", "SPIRAM_MODE_OCT": True, "NOMI_WAKE_BENCHMARK": False}
        self.args = {"flash_files": {"0x0":"bootloader/bootloader.bin", "0x8000":"partition_table/partition-table.bin",
                                    "0x10000":"desktop_nomi_h2.bin", "0x410000":"srmodels/srmodels.bin"}}
        self.write()

    def write(self, count=0, model=b"wn9_xiaoaitongxue"):
        (self.root/"config/sdkconfig.json").write_text(json.dumps(self.config))
        (self.root/"flasher_args.json").write_text(json.dumps(self.args))
        (self.root/"srmodels/srmodels.bin").write_bytes(struct.pack("<I", count) + (model.ljust(32,b"\0") + struct.pack("<I", 0) if count else b""))

    def audit(self, profile="audio", symbols=""):
        with patch.object(build_tool.shutil,"which",return_value="fake-nm"), patch.object(build_tool.subprocess,"check_output",return_value=symbols):
            return build_tool.validate(self.root,profile)

    def test_audio_has_no_wake_model(self):
        self.audit()
        self.write(1)
        with self.assertRaises(ValueError): self.audit()

    def test_benchmark_requires_exact_identity(self):
        self.config["NOMI_WAKE_BENCHMARK"] = True
        self.write(1); self.audit("benchmark")
        self.write(1,b"wn9_xiaomingtongxue_tts2")
        with self.assertRaises(ValueError): self.audit("benchmark")
        self.write(0)
        with self.assertRaises(ValueError): self.audit("benchmark")

    def test_commands_requires_exact_pair_and_recognizer(self):
        self.config["NOMI_VOICE_COMMANDS"] = True
        self.write()
        def record(name): return name.ljust(32,b"\0") + struct.pack("<I",0)
        blob = struct.pack("<I",2) + record(b"fst") + record(b"mn7_cn")
        (self.root/"srmodels/srmodels.bin").write_bytes(blob)
        self.audit("commands", "esp_mn_handle_from_name")
        with self.assertRaises(ValueError): self.audit("commands")
        with self.assertRaises(ValueError): self.audit("commands", "esp_mn_handle_from_name esp_wifi_init")
        (self.root/"srmodels/srmodels.bin").write_bytes(blob[:-1])
        with self.assertRaises(ValueError): self.audit("commands", "esp_mn_handle_from_name")

    def test_wrong_profile_and_offsets(self):
        with self.assertRaises(ValueError): self.audit("benchmark")
        self.args["flash_files"]["0x420000"] = self.args["flash_files"].pop("0x410000")
        self.write()
        with self.assertRaises(ValueError): self.audit()

    def test_reject_wrong_chip_or_network_and_recognition(self):
        for symbol in ("esp_wifi_init","esp_http_client_init","esp_tls_conn_new","esp_mn_handle_from_name","esp_tts_create"):
            with self.subTest(symbol=symbol), self.assertRaises(ValueError): self.audit(symbols=symbol)
        self.config["IDF_TARGET"]="esp32"
        self.write()
        with self.assertRaises(ValueError): self.audit()


if __name__ == "__main__": unittest.main()
