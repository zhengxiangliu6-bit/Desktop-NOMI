import importlib.util
from pathlib import Path
import tempfile
import unittest
import wave
spec=importlib.util.spec_from_file_location('import_reply',Path(__file__).parents[1]/'scripts/import_reply.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class ImportReplyTests(unittest.TestCase):
    def test_rejects_stereo_wrong_rate_float_silence_clipping_and_oversize(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'reply.wav'
            for channels,rate,sample,count,valid in [(1,16000,100,8545,True),(2,16000,100,8545,False),
                    (1,22050,100,8545,False),(1,16000,0,8545,False),(1,16000,32767,8545,False),
                    (1,16000,100,48001,False)]:
                with wave.open(str(p),'wb') as w:
                    w.setnchannels(channels);w.setsampwidth(2);w.setframerate(rate)
                    w.writeframes(int(sample).to_bytes(2,'little',signed=True)*count*channels)
                if valid:self.assertEqual(len(module.read_wav(p)),count*2)
                else:
                    with self.assertRaises(ValueError):module.read_wav(p)
            p.write_bytes(b'not a WAV; do not rename MP3')
            with self.assertRaises((wave.Error,EOFError)):module.read_wav(p)
