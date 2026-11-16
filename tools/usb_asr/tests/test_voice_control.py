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
        self.assertIsNone(c.tick(2))
        self.assertEqual(c.until,20) # display renewal must never extend conversational expiry
        self.assertEqual(c.final('开心一点',3).command,'happy')
        self.assertIsNone(c.tick(7.9))
        self.assertIsNone(c.tick(8.1))
        self.assertEqual(c.tick(23).command,'idle')
        self.assertIsNone(c.final('开心一点',24).command)
        c.final('小米同学',25)
        self.assertEqual(c.final('休息一下',26).command,'idle')
        self.assertIsNone(c.final('难过一点',27).command)
        self.assertIsNone(c.tick(99))

    def test_rewake_only_extends_and_never_schedules_periodic_commands(self):
        c=VoiceControl();self.assertEqual(c.final('小米同学',0).command,'listening')
        self.assertEqual(c.final('开心一点',2).command,'happy')
        self.assertEqual(c.final('小米同学',5).command,'extend')
        self.assertEqual(c.until,25)
        for now in range(6,25):self.assertIsNone(c.tick(now))
        self.assertEqual(c.tick(25).command,'idle')
        self.assertIsNone(c.tick(27))

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


def ack(token,seq,command,status='OK'):
    from protocol import checksum
    payload=f'{command} {status}'.encode()
    return f'@NOMI_ACK1 {token:08x} {seq:08x} {command} {status} {checksum(token,seq,0,payload):08x}'.encode()


class ChannelTests(unittest.TestCase):
    def setUp(self):
        self.now=0;self.events=[];self.written=[]
        self.c=CommandChannel(lambda:self.now,lambda *v:self.events.append(v),123)
        self.c.tick(self.written.append)
        self.assertIn(b'00000000 probe 0',self.written[-1])
        self.c.observe(ack(123,0,'probe'))

    def test_matches_token_sequence_command_and_checksum(self):
        self.c.submit('listening','wake');self.c.tick(self.written.append)
        self.c.observe(b'nomi: Command accepted: listening (5s TTL)')
        self.assertIsNotNone(self.c.pending)
        self.c.observe(ack(999,1,'listening'))
        self.assertIsNotNone(self.c.pending)
        self.c.observe(ack(123,1,'listening'))
        self.assertIsNone(self.c.pending)
        self.c.submit('listening','later');self.c.tick(self.written.append)
        self.c.observe(ack(123,1,'listening')) # delayed duplicate cannot confirm request #2
        self.assertIsNotNone(self.c.pending)
        self.c.observe(ack(123,2,'listening'))
        self.assertIsNone(self.c.pending)

    def test_missing_wrong_corrupt_or_rejected_ack_fails_closed(self):
        self.c.submit('happy','face');self.c.tick(self.written.append)
        with self.assertRaises(ProtocolError):self.c.observe(ack(123,1,'idle'))
        with self.assertRaises(ProtocolError):self.c.observe(ack(123,1,'happy')[:-1]+b'0')
        with self.assertRaises(ProtocolError):self.c.observe(ack(123,1,'happy','STALE'))
        self.now=1.6
        with self.assertRaises(ProtocolError):self.c.tick(self.written.append)

    def test_rejects_unsupported_stale_and_overflow(self):
        with self.assertRaises(ValueError):self.c.submit('erase_flash','bad')
        self.c.submit('idle','sleep');self.now=1.1
        with self.assertRaises(ProtocolError):self.c.tick(self.written.append)
        for _ in range(8):self.c.submit('idle','sleep')
        with self.assertRaises(ProtocolError):self.c.submit('idle','overflow')

    def test_old_firmware_cannot_handshake_with_log_ack(self):
        c=CommandChannel(lambda:self.now,lambda *x:None,123)
        c.tick(self.written.append)
        c.observe(b'nomi: Command accepted: listening (5s TTL)')
        self.now=1.6
        with self.assertRaisesRegex(ProtocolError,'0.4.3'):c.tick(self.written.append)


if __name__=='__main__':unittest.main()
