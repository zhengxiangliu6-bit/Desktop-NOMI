from pathlib import Path
import sys,base64,struct,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from protocol import FrameParser,checksum,ProtocolError
from recognition_gate import RecognitionGate
from command_channel import CommandChannel
from test_voice_control import ack

class ReplyTests(unittest.TestCase):
    def test_playback_flags_are_checked_and_cannot_leak_to_asr(self):
        p=FrameParser(1);pcm=bytes(640)
        def frame(seq,flags):
            return f'@NOMI2 00000001 {seq:08x} 1 {flags} {checksum(1,seq,1,bytes([flags])+pcm):08x} '.encode()+base64.b64encode(pcm)
        self.assertEqual(p.parse(frame(0,1)),pcm);self.assertTrue(p.guarded)
        damaged=frame(1,0).replace(b' 1 0 ',b' 1 1 ')
        with self.assertRaises(ProtocolError):p.parse(damaged)
        p.parse(frame(1,0));self.assertFalse(p.guarded)
        class Decoder:
            def __init__(self):self.resets=0;self.feeds=0
            def reset(self):self.resets+=1
            def feed(self,pcm):self.feeds+=1;return [('最终','小米同学')]
        d=Decoder();g=RecognitionGate(lambda *x:None)
        self.assertEqual(g.feed(d,pcm,True),[])
        self.assertEqual(g.feed(d,pcm,True),[])
        self.assertEqual(d.feeds,0);self.assertEqual(d.resets,1)
        g.feed(d,pcm,False);self.assertEqual((d.resets,d.feeds),(2,1))

    def test_speak_only_for_spoken_commands_not_probe_extend_or_timeout(self):
        lines=[];c=CommandChannel(lambda:0,lambda *x:None,1)
        c.tick(lines.append);self.assertTrue(lines[-1].endswith(b'probe 0\r\n'));c.observe(ack(1,0,'probe'))
        for seq,cmd,spoken,expected in [(1,'happy',True,1),(2,'extend',True,0),(3,'idle',False,0),(4,'idle',True,1)]:
            c.submit(cmd,'test',spoken);c.tick(lines.append)
            self.assertTrue(lines[-1].endswith(f'{cmd} {expected}\r\n'.encode()))
            c.observe(ack(1,seq,cmd))

    def test_playback_events_do_not_confirm_commands_and_error_is_visible(self):
        reports=[];c=CommandChannel(lambda:0,lambda *x:reports.append(x),1)
        c.tick(lambda data:len(data))
        def event(name,token=1):
            return f'@NOMI_SAY1 {token:08x} 00000001 {name} {checksum(token,1,0,name.encode()):08x}'.encode()
        c.observe(event('START',9));self.assertEqual(len(reports),1) # only handshake send
        c.observe(event('START'));self.assertIsNotNone(c.pending) # audio event is not control ACK
        c.observe(event('DONE'));self.assertTrue(any(x[0]=='回应' for x in reports))
        with self.assertRaises(ProtocolError):c.observe(event('ERROR'))

    def test_late_final_timeout_is_quiet(self):
        from voice_control import VoiceControl,route_result
        c=VoiceControl();c.final('小米同学',0)
        calls=[]
        route_result('最终','开心一点',c,lambda *x:calls.append(x),lambda *x:None,21)
        self.assertEqual(calls[0][0],'idle')
        self.assertFalse(calls[0][2]) # late result is rejected; expiry is not a spoken instruction
