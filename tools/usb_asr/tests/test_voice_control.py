from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from voice_control import VoiceControl,FACES,normalize,route_result
from command_channel import CommandChannel
from protocol import ProtocolError


class VoiceControlTests(unittest.TestCase):
    def test_requires_wake_and_exact_phrases(self):
        c=VoiceControl()
        self.assertIsNone(c.final('开心一点',0).command)
        self.assertEqual(c.final('你好，小米同学！',1).command,'listening')
        for text in ['小爱同学','小明同学','不要开心一点','他说开心一点','开心一些','小米同学开心一点']:
            self.assertIsNone(c.final(text,2).command,text)
        for i,(text,cmd) in enumerate(FACES.items()):
            self.assertEqual(c.final(text,3+i*2).command,cmd)
        self.assertEqual(normalize(' 开心 一点。'),'开心一点')

    def test_partial_and_stopped_finals_never_reach_serial_queue(self):
        c=VoiceControl();requests=[];reports=[]
        send=lambda *r:requests.append(r)
        report=lambda *r:reports.append(r)
        route_result('临时','小米同学',c,send,report,0)
        self.assertEqual(requests,[])
        route_result('最终','小米同学',c,send,report,1)
        self.assertEqual(requests[0][0],'listening')
        route_result('临时','开心一点',c,send,report,2)
        route_result('最终','开心一点',c,send,report,3,stopped=True)
        self.assertEqual(len(requests),1)
        route_result('最终','开心一点',c,send,report,4)
        self.assertEqual(requests[-1][0],'happy')

    def test_timeout_sleep_renew_and_duplicate(self):
        c=VoiceControl();c.final('小米同学',0)
        self.assertIsNone(c.final('小米同学',0.5).command)
        self.assertEqual(c.tick(2).command,'listening')
        self.assertEqual(c.until,20) # display renewal must never extend conversational expiry
        self.assertEqual(c.final('开心一点',3).command,'happy')
        self.assertIsNone(c.tick(7.9))
        self.assertEqual(c.tick(8.1).command,'listening')
        self.assertEqual(c.tick(23).command,'idle')
        self.assertIsNone(c.final('开心一点',24).command)
        c.final('小米同学',25)
        self.assertEqual(c.final('休息一下',26).command,'idle')
        self.assertIsNone(c.final('难过一点',27).command)
        self.assertIsNone(c.tick(99))

    def test_late_final_does_not_bypass_timeout(self):
        c=VoiceControl();c.final('小米同学',1)
        self.assertEqual(c.final('开心一点',22).command,'idle')
        self.assertIsNone(c.final('开心一点',24).command)
        self.assertEqual(c.final('小米同学',25).command,'listening')

    def test_custom_name_and_safety(self):
        c=VoiceControl('小诺同学')
        self.assertIsNone(c.final('小米同学',1).command)
        self.assertEqual(c.final('你好小诺同学',2).command,'listening')
        self.assertEqual(c.final('回到待机',3).command,'idle')
        with self.assertRaises(ValueError):VoiceControl('开心一点')
        with self.assertRaises(ValueError):c.final('你好',float('nan'))


class ChannelTests(unittest.TestCase):
    def setUp(self):
        self.now=0;self.events=[];self.written=[]
        self.c=CommandChannel(lambda:self.now,lambda *v:self.events.append(v))

    def test_serializes_requests_and_recovers_log_fragments(self):
        self.c.submit('listening','wake');self.c.submit('happy','face')
        self.c.tick(self.written.append)
        self.assertEqual(self.written,[b'listening\r\n'])
        self.c.observe(b'\x1b[0;32mI (120) nomi: Command accep')
        self.c.tick(self.written.append)
        self.assertEqual(len(self.written),1)
        self.c.observe(b'ted: listening (5s TTL)\x1b[0m')
        self.assertIsNone(self.c.pending)
        self.c.tick(self.written.append)
        self.assertEqual(self.written[-1],b'happy\r\n')
        self.c.observe(b'I (130) nomi: Command accepted: happy (5s TTL)')
        self.assertEqual(sum(e[0]=='设备确认' for e in self.events),2)

    def test_missing_wrong_or_old_ack_is_not_success(self):
        self.c.observe(b'I (100) nomi: Command accepted: happy (5s TTL)')
        self.c.submit('happy','face');self.c.tick(self.written.append)
        self.assertIsNotNone(self.c.pending)
        self.now=1.6
        with self.assertRaises(ProtocolError):self.c.tick(self.written.append)
        self.assertFalse(any(e[0]=='设备确认' for e in self.events))
        with self.assertRaises(ProtocolError):self.c.observe(b'I (120) nomi: Command accepted: idle (5s TTL)')

    def test_rejects_unsupported_stale_and_overflow(self):
        with self.assertRaises(ValueError):self.c.submit('erase_flash','bad')
        self.c.submit('idle','sleep');self.now=1.1
        with self.assertRaises(ProtocolError):self.c.tick(self.written.append)
        self.assertEqual(self.written,[])
        for _ in range(8):self.c.submit('idle','sleep')
        with self.assertRaises(ProtocolError):self.c.submit('idle','overflow')


if __name__=='__main__':unittest.main()
