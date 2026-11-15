import base64
from pathlib import Path
import queue
import struct
import sys
import threading
import time
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from protocol import checksum,FrameParser,ProtocolError
from transcribe import BoardReader


def frame(seq=0, token=0x12345678, channel=1, pcm=None):
    pcm = pcm if pcm is not None else struct.pack('<320h', *([0,1,-1,-32768,32767]*64))
    return f'@NOMI1 {token:08x} {seq:08x} {channel} {checksum(token,seq,channel,pcm):08x} '.encode()+base64.b64encode(pcm)+b'\n'


class ProtocolTests(unittest.TestCase):
    def test_pcm_endian_extremes_and_logs(self):
        p=FrameParser(0x12345678)
        self.assertIsNone(p.parse('I: 初始化就绪'.encode()))
        pcm=p.parse(frame())
        self.assertEqual(struct.unpack('<5h',pcm[:10]),(0,1,-1,-32768,32767))
        self.assertEqual(p.frames,1)
        self.assertEqual(checksum(0x12345678,0,1,pcm),0xbbde03bc) # shared C++ golden vector

    def test_integrity_sequence_session_and_channel(self):
        self.assertIsNone(FrameParser(1).parse(frame()))
        for bad in [frame(seq=1),frame(channel=2),frame()[:-5]+b'****',frame(pcm=b'\0\0')]:
            with self.subTest(bad=bad[:45]),self.assertRaises(ProtocolError): FrameParser(0x12345678).parse(bad)
        p=FrameParser(0x12345678);p.parse(frame())
        with self.assertRaises(ProtocolError):p.parse(frame())

    def test_reader_start_ping_stop_and_queue_backpressure(self):
        class Serial:
            def __init__(self): self.writes=[];self.sent=False
            def write(self,data): self.writes.append(data);return len(data)
            def read(self,n):
                if not self.sent: self.sent=True; return frame()+frame(1)
                time.sleep(0.01);return b''
        port=Serial();stop=threading.Event();output=queue.Queue(maxsize=1)
        reader=BoardReader(port,0x12345678,1,output,stop);reader.start();reader.join(1)
        self.assertFalse(reader.is_alive());self.assertTrue(stop.is_set())
        self.assertIn('积压',str(reader.error))
        self.assertTrue(port.writes[0].startswith(b'stream on '))
        self.assertTrue(any(x.startswith(b'stream ping ') for x in port.writes))
        self.assertEqual(port.writes[-1],b'stream off\r\n')

    def test_reader_rejects_corruption_and_stops(self):
        class Serial:
            def __init__(self):self.writes=[]
            def write(self,data):self.writes.append(data);return len(data)
            def read(self,n):return frame(seq=9)
        port=Serial();reader=BoardReader(port,0x12345678,1,queue.Queue(25),threading.Event())
        reader.run()
        self.assertIsInstance(reader.error,ProtocolError)
        self.assertEqual(port.writes[-1],b'stream off\r\n')



class ControlReaderTests(unittest.TestCase):
    def test_control_ack_split_by_pcm_and_shutdown(self):
        from command_channel import CommandChannel
        reports=[];stop=threading.Event();output=queue.Queue(25)
        channel=CommandChannel(time.monotonic,lambda *x:reports.append(x),0x12345678)
        channel.submit('happy','test final phrase')
        class Serial:
            def __init__(self):self.writes=[];self.sent=False
            def write(self,data):self.writes.append(data);return len(data)
            def read(self,n):
                if not self.sent:
                    self.sent=True
                    from test_voice_control import ack
                    return frame()+ack(0x12345678,0,'probe')+b'\n'
                if channel.pending and channel.pending.command=='happy':
                    from test_voice_control import ack
                    self.happy=True
                    return ack(0x12345678,1,'happy')+b'\n'
                if getattr(self,'happy',False):stop.set()
                return b''
        port=Serial();reader=BoardReader(port,0x12345678,1,output,stop,channel)
        reader.run()
        self.assertIsNone(reader.error)
        self.assertEqual(reader.parser.frames,1)
        self.assertTrue(any(b'00000001 happy' in w for w in port.writes))
        self.assertEqual(port.writes[-2:],[b'idle\r\n',b'stream off\r\n'])
        self.assertTrue(any(x[0]=='设备确认' for x in reports))

    def test_short_control_write_is_an_error(self):
        class Serial:
            def write(self,data):return len(data)-1
        reader=BoardReader(Serial(),1,1,queue.Queue(25),threading.Event())
        reader.run()
        self.assertIsInstance(reader.error,ProtocolError)

if __name__=='__main__':unittest.main()
