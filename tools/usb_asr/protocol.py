"""Versioned USB board-microphone frames. No hardware/model dependencies."""
import base64
import binascii
import struct

SAMPLE_RATE = 16000
SAMPLES = 320


class ProtocolError(ValueError):
    pass


def checksum(token, sequence, channel, pcm):
    value = 2166136261
    for byte in struct.pack('<IIB', token, sequence, channel) + pcm:
        value = ((value ^ byte) * 16777619) & 0xffffffff
    return value


class FrameParser:
    def __init__(self, token, channel=1):
        self.token = token
        self.channel = channel
        self.expected = 0
        self.frames = 0
        self.guarded = False

    def parse(self, line):
        """None means unrelated log/old session, never fabricated PCM or text."""
        if not line.startswith((b'@NOMI1 ',b'@NOMI2 ')):
            return None
        parts = line.strip().split()
        # Old session frames are deliberately ignored, not treated as fresh microphone data.
        try:
            if len(parts) >= 2 and int(parts[1], 16) != self.token:
                return None
            v2=parts[0]==b'@NOMI2'
            if len(parts) != (7 if v2 else 6):
                raise ValueError('field count')
            if v2:
                _,token,seq,channel,flags,digest,payload=parts
                flags=int(flags)
                if flags not in (0,1): raise ValueError("guard flags")
            else:
                _,token,seq,channel,digest,payload=parts
                flags=0
            token, seq, channel, digest = int(token,16), int(seq,16), int(channel), int(digest,16)
            if not 0 <= seq <= 0xffffffff or channel != self.channel:
                raise ValueError('sequence/channel range')
            pcm = base64.b64decode(payload, validate=True)
            if len(pcm) != SAMPLES*2 or checksum(token, seq, channel, (bytes([flags]) if v2 else b'')+pcm) != digest:
                raise ValueError('length/checksum')
            if seq != self.expected:
                raise ValueError(f'frame gap: expected {self.expected}, received {seq}')
        except (ValueError, binascii.Error) as error:
            raise ProtocolError(f'音频帧损坏或丢失：{error}') from error
        self.expected = (seq+1) & 0xffffffff
        self.frames += 1
        self.guarded = bool(flags)
        return pcm
