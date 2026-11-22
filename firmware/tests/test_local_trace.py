import importlib.util,unittest,struct,base64
from pathlib import Path
spec=importlib.util.spec_from_file_location('trace_monitor',Path(__file__).parents[2]/'tools/local_voice_debug/monitor.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class TraceTests(unittest.TestCase):
    def line(self,ch,seq=0,token=1):
        pcm=struct.pack('<320h',*range(320));flags=0
        return f'@NTRC1 {token:08x} {seq:08x} {ch} {flags} {m.checksum(token,seq,ch,bytes([flags])+pcm):08x} '.encode()+base64.b64encode(pcm)
    def test_independent_channels_sequence_integrity_and_wrong_session(self):
        p=m.TraceParser(1)
        self.assertIsNone(p.parse(self.line(1,token=2)))
        self.assertEqual(p.parse(self.line(1))[0],1);self.assertEqual(p.parse(self.line(2))[0],2)
        self.assertEqual(p.parse(self.line(1,1))[2],struct.pack('<320h',*range(320)))
        with self.assertRaises(ValueError):p.parse(self.line(1,3))
        p=m.TraceParser(1)
        with self.assertRaises(ValueError):p.parse(self.line(1)[:-2]+b'AA')
        self.assertIsNone(p.parse(b'@NOMI2 unrelated PC ASR protocol'))
