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

    def test_private_output_does_not_change_stock_asset_or_copy_source_path(self):
        from unittest.mock import patch
        import json,hashlib
        stock=module.ROOT/'components/nomi_audio/assets/okay.pcm'
        before=hashlib.sha256(stock.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/'input.wav';out=Path(temp)/'private'
            with wave.open(str(source),'wb') as w:
                w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000);w.writeframes(b'\x64\x00'*4000)
            with patch('sys.argv',['import_reply.py',str(source),'--output-dir',str(out)]):module.main()
            meta=json.loads((out/'okay.json').read_text())
            self.assertEqual(meta['bytes'],8000)
            self.assertNotIn(str(source),json.dumps(meta))
            self.assertEqual(hashlib.sha256(stock.read_bytes()).hexdigest(),before)
            self.assertEqual(sorted(x.name for x in out.iterdir()),['NOTICE.md','okay.json','okay.pcm'])
