"""Correlated atomic replies; never use ordinary device logs as control acknowledgments."""
from dataclasses import dataclass
import queue
import re
from voice_control import ALLOWED_COMMANDS
from protocol import ProtocolError, checksum

ACK=re.compile(rb'^@NOMI_ACK1 ([0-9a-f]{8}) ([0-9a-f]{8}) ([a-z]+) ([A-Z]+) ([0-9a-f]{8})$')


@dataclass(frozen=True)
class Request:
    command: str
    reason: str
    at: float


class CommandChannel:
    def __init__(self, clock, report, token):
        self.clock,self.report,self.token=clock,report,token
        self.requests=queue.Queue(maxsize=8)
        self.pending=None
        self.sent_at=0.0
        self.touched=False
        self.sequence=0
        self.ready=False

    def submit(self, command, reason):
        if command not in ALLOWED_COMMANDS: raise ValueError('Unsupported board command')
        try:self.requests.put_nowait(Request(command,reason,self.clock()))
        except queue.Full as error:raise ProtocolError('表情指令队列已满，停止控制') from error

    def tick(self, write):
        now=self.clock()
        if self.pending:
            if now-self.sent_at>1.5:
                stage='需要配套0.4.2固件；协议握手' if self.pending.command=='probe' else self.pending.command
                raise ProtocolError(f'设备未在1.5秒内确认 {stage}；不能宣称已执行')
            return
        if not self.ready:request=Request('probe','确认编号回执协议',now)
        else:
            try:request=self.requests.get_nowait()
            except queue.Empty:return
            if now-request.at>1:raise ProtocolError('表情指令积压超过1秒，停止而不执行过期动作')
        self.pending,self.sent_at=request,now
        write(f'ctl {self.token:08x} {self.sequence:08x} {request.command}\r\n'.encode('ascii'))
        if request.command!='probe':self.touched=True
        self.report('发送',f'{request.command} #{self.sequence}；{request.reason}；等待编号回执')

    def observe(self, fragment):
        match=ACK.fullmatch(fragment.strip())
        if not match:return # Logs, including legacy ACK text, have no control authority.
        token,seq,command,status,digest=match.groups()
        token,seq,digest=int(token,16),int(seq,16),int(digest,16)
        if token!=self.token:return
        payload=command+b' '+status
        if checksum(token,seq,0,payload)!=digest:raise ProtocolError('控制回执校验失败')
        if not self.pending or seq<self.sequence:return # Duplicate/late response cannot confirm a newer command.
        if seq!=self.sequence or command.decode()!=self.pending.command:raise ProtocolError('控制回执编号/动作不一致')
        if status!=b'OK':raise ProtocolError(f'设备拒绝指令：{status.decode()}')
        if self.pending.command=='probe':
            self.ready=True;self.report('设备确认','0.4.2编号回执协议就绪')
        else:self.report('设备确认',f'已接受 {self.pending.command} #{seq}（请观察实际屏幕效果）')
        self.pending=None;self.sequence+=1
