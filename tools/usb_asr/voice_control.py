"""Deterministic final-text control. No ASR, serial, clocks, or fuzzy matching here."""
from dataclasses import dataclass
import math
import unicodedata

FACES = {
    '开心一点': 'happy', '开心一下': 'happy', '难过一点': 'sad', '难过一下': 'sad', '眨一下眼': 'blink', '眨眼一下': 'blink',
    '好奇一点': 'curious', '思考一下': 'thinking', '认真听讲': 'listening',
    '说话表情': 'speaking',
}
SLEEP = {'休息一下', '回到待机'}
ALLOWED_COMMANDS = frozenset({'idle', 'blink', 'happy', 'sad', 'curious', 'thinking', 'listening', 'speaking', 'extend'})


def normalize(text):
    # Permit ASR punctuation/spacing, never delete negation or arbitrary words.
    return ''.join(c for c in unicodedata.normalize('NFKC', text)
                   if not c.isspace() and not unicodedata.category(c).startswith('P'))


@dataclass(frozen=True)
class Decision:
    command: str | None
    reason: str
    accepted: bool = True


class VoiceControl:
    WINDOW = 20.0

    def __init__(self, wake_name='小米同学'):
        wake_name = normalize(wake_name)
        if not 2 <= len(wake_name) <= 12 or wake_name in FACES or wake_name in SLEEP:
            raise ValueError('激活名称需2–12个字符，且不能与表情/休息指令相同')
        self.wake_names = {wake_name, '你好'+wake_name}
        self.until = 0.0
        self.last_text = ''
        self.last_at = -float('inf')

    def tick(self, now):
        if self.until and now >= self.until:
            self.until = 0.0
            return Decision('idle', '20秒没有接受到新指令，回到待机')
        return None

    def final(self, text, now):
        if not math.isfinite(now):
            raise ValueError('Invalid clock')
        value = normalize(text)
        # Expiry must be handled even when the only event is a late final result.
        if self.until and now >= self.until:
            self.until = 0.0
            if value not in self.wake_names:
                return Decision('idle', '会话已超时，本句不执行；请重新唤醒', accepted=False)
        if not value:
            return Decision(None, '没有最终识别文字')
        if value == self.last_text and 0 <= now-self.last_at < 1.2:
            return Decision(None, '短时间重复的最终结果')
        self.last_text, self.last_at = value, now
        if value in self.wake_names:
            already_awake = bool(self.until and now<self.until)
            self.until = now+self.WINDOW
            return Decision('extend' if already_awake else 'listening',
                            '已在聆听，仅续期20秒，不重置当前表情' if already_awake else '已接受唤醒，20秒内可说表情指令')
        if not self.until:
            return Decision(None, '尚未唤醒；请先说激活名称')
        if value in SLEEP:
            self.until = 0.0
            return Decision('idle', '已接受休息，回到待机')
        if value not in FACES:
            return Decision(None, '不是已配置指令；不做模糊匹配')
        self.until = now+self.WINDOW
        # Firmware owns display TTL and Listening fallback; no periodic serial refresh.
        return Decision(FACES[value], '已接受表情指令，聆听窗口续期20秒')


def route_result(kind, text, control, submit, report, now, stopped=False):
    """Only committed live ASR finals may reach the command queue."""
    if control is None or kind != '最终':
        return
    if stopped:
        report('忽略', '采音或控制已停止，本句不执行')
        return
    decision = control.final(text, now)
    report('接受' if decision.command and decision.accepted else '忽略', decision.reason)
    if decision.command:
        submit(decision.command, decision.reason, decision.accepted)
