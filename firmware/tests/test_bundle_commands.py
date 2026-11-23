import importlib.util
from pathlib import Path
import struct
import unittest

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("bundle", root / "scripts/bundle_commands.py")
bundle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bundle)


class BundleCommandsTest(unittest.TestCase):
    def test_replacement_preserves_other_payload_and_can_be_repeated(self):
        start = 4 + 36 + 80
        image = struct.pack("<I32sI", 1, b"fst", 2)
        image += struct.pack("<32sII", b"commands_cn.txt", start, 3)
        image += struct.pack("<32sII", b"other", start+3, 4)
        image += b"oldkeep"
        header = (root / "main/voice/voice_session.h").read_text(encoding="utf-8")
        result = bundle.bundle_commands(image, header, "xiao mi tong xue")
        _, index, length = struct.unpack_from("<32sII", result, 40)
        words = result[index:index+length].splitlines()
        self.assertEqual(len(words), 18)
        self.assertEqual(words[0], b"1,xiao mi tong xue")
        self.assertEqual(words[-1], b"25,da kai kong tiao")
        _, index, length = struct.unpack_from("<32sII", result, 80)
        self.assertEqual(result[index:index+length], b"keep")
        self.assertEqual(bundle.bundle_commands(result, header, "xiao mi tong xue"), result)
