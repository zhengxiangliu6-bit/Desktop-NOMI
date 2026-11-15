"""Single-writer serial control with legacy firmware acceptance acknowledgments."""
from dataclasses import dataclass
import queue
import re
from voice_control import ALLOWED_COMMANDS
from protocol import ProtocolError

ANSI = re.compile(rb'\x1b\[[0-9;]*[A-Za-z]')
ACK = re.compile(rb'nomi: Command accepted: (idle|blink|happy|sad|curious|thinking|listening|speaking) \(5s TTL\)')


@dataclass(frozen=True)
class Request:
    command: str
    reason: str
    at: float


class CommandChannel:
    def __init__(self, clock, report):
        self.clock, self.report = clock, report
        self.requests = queue.Queue(maxsize=8)
        self.pending = None
        self.sent_at = 0.0
        self.log = bytearray()
        self.touched = False

    def submit(self, command, reason):
        if command not in ALLOWED_COMMANDS:
            raise ValueError('Unsupported board command')
        try:
            self.requests.put_nowait(Request(command, reason, self.clock()))
        except queue.Full as error:
            raise ProtocolError('表情指令队列已满，停止控制') from error

    def tick(self, write):
        now = self.clock()
        if self.pending:
            if now-self.sent_at > 1.5:
                raise ProtocolError(f'设备未在1.5秒内确认 {self.pending.command}；不能宣称已执行')
            return
        try:
            request = self.requests.get_nowait()
        except queue.Empty:
            return
        if now-request.at > 1.0:
            raise ProtocolError('表情指令积压超过1秒，停止而不执行过期动作')
        self.pending, self.sent_at, self.touched = request, now, True
        write((request.command+'\r\n').encode('ascii'))
        self.report('发送', f'{request.command}；{request.reason}；等待设备确认')

    def observe(self, fragment):
        # IDF VFS writes logs character-by-character. Atomic PCM frames can be inserted
        # between log fragments; join non-PCM fragments without changing audio parsing.
        self.log.extend(ANSI.sub(b'',fragment).replace(b'\r',b'').replace(b'\n',b''))
        self.log = self.log[-4096:]
        while match := ACK.search(self.log):
            command = match.group(1).decode('ascii')
            del self.log[:match.end()]
            if not self.pending:
                continue # Never let an unsolicited/old complete acknowledgment arm the next command.
            if command != self.pending.command:
                raise ProtocolError('设备回执与等待中的指令不一致，停止控制')
            self.report('设备确认', f'已接受 {command}（请观察实际屏幕效果）')
            self.pending = None
