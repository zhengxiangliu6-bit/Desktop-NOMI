"""Explicitly started local Chinese ASR from ESP32 USB PCM; no recording/network runtime."""
import argparse
import math
import queue
import secrets
import struct
import sys
import threading
import time
from pathlib import Path
from protocol import FrameParser, ProtocolError
from setup_model import verify_model
from voice_control import VoiceControl, route_result
from command_channel import CommandChannel


PRINT_LOCK = threading.Lock()


def out(kind, text):
    with PRINT_LOCK:
        print(f'[{kind}] {text}', flush=True)


class BoardReader(threading.Thread):
    """Always drains USB/pings separately from inference; bounded queue fails closed."""
    def __init__(self, serial, token, mic, output, stop, commands=None):
        super().__init__(daemon=True)
        self.serial, self.token, self.mic = serial, token, mic
        self.output, self.stop = output, stop
        self.error = None
        self.parser = FrameParser(token, mic)
        self.commands = commands

    def write(self, data):
        if self.serial.write(data) != len(data):
            raise ProtocolError('串口指令短写，停止采音/控制')

    def run(self):
        pending = bytearray()
        deadline = time.monotonic()+8
        ping_at = 0
        start_at = time.monotonic()+1
        try:
            self.write(f'stream on {self.token:08x} {self.mic}\r\n'.encode())
            while not self.stop.is_set():
                now = time.monotonic()
                if self.parser.frames == 0 and now >= start_at:
                    self.write(f'stream on {self.token:08x} {self.mic}\r\n'.encode())
                    start_at = now+1 # Opening USB can reset some Windows devices; retry startup only.
                if now >= ping_at:
                    self.write(f'stream ping {self.token:08x}\r\n'.encode())
                    ping_at = now+0.4
                if self.commands:
                    self.commands.tick(self.write)
                pending.extend(self.serial.read(4096))
                if len(pending) > 16384:
                    raise ProtocolError('串口行过长：请确认烧录的是USB转录调试固件')
                while b'\n' in pending:
                    line, _, remainder = pending.partition(b'\n')
                    pending = bytearray(remainder)
                    pcm = self.parser.parse(bytes(line).strip())
                    if pcm is not None:
                        try:
                            self.output.put_nowait((time.monotonic(), pcm))
                        except queue.Full:
                            raise ProtocolError('电脑识别处理跟不上：音频积压超过0.5秒，已停止，不丢帧继续识别')
                        deadline = time.monotonic()+2
                    elif b'STREAM_FAULT' in line:
                        raise ProtocolError('设备报告采音或USB传输故障；请重启本程序并检查设备')
                    else:
                        if self.commands:
                            self.commands.observe(bytes(line))
                    if pcm is None and any(tag in line for tag in (b'usb_audio:', b'nomi_audio:', b'ES7210', b'ES8311', b'Guru Meditation')):
                        out('设备', line.decode('utf-8', errors='replace'))
                if time.monotonic() >= deadline:
                    raise ProtocolError('未收到连续音频：请确认新固件、数据线、COM端口，且已关闭miniterm')
        except Exception as error:
            self.error = error
            self.stop.set()
        finally:
            try:
                if self.commands and self.commands.touched:
                    self.write(b'idle\r\n')
                    out('停止', '已发送待机请求；退出阶段未等待设备回执。')
            except Exception:
                pass
            try:
                self.write(b'stream off\r\n')
            except Exception:
                pass # Device also has a 2s heartbeat lease and finite USB write timeout.


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', default='COM3')
    parser.add_argument('--mic', type=int, choices=(1,2), default=1)
    parser.add_argument('--voice-control', action='store_true', help='仅最终中文结果触发表情；默认仍为纯转录')
    parser.add_argument('--wake-name', default='小米同学')
    parser.add_argument('--threads', type=int, choices=range(1,9), default=2)
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    from recognizer import ChineseRecognizer
    import serial
    out('版本', 'PC语音控制0.4.1；兼容已验证的USB采音固件0.4.0，无需重新烧录。')
    out('准备', '加载电脑本地中文模型；音频来自ESP32板载麦克风，不上传、不保存录音或转录。')
    recognizer = ChineseRecognizer(verify_model(), args.threads)
    input('按 Enter 开始麦克风采集；Ctrl+C 停止：')
    control = VoiceControl(args.wake_name) if args.voice_control else None
    channel = CommandChannel(time.monotonic, out) if control else None
    stop = threading.Event()
    frames = queue.Queue(maxsize=25) # 500ms total queued audio, never unbounded retention.
    with serial.Serial(args.port, 115200, timeout=0.05, write_timeout=0.5) as port:
        port.reset_input_buffer()
        reader = BoardReader(port, secrets.randbelow(0xffffffff)+1, args.mic, frames, stop, channel)
        reader.start()
        out('状态', f'已请求 {args.port} / 板载MIC{args.mic}。')
        out('控制', f'已启用：先说“{args.wake_name}”或“你好{args.wake_name}”，看到设备确认后再说表情指令。' if control else '纯转录模式：不需要唤醒，不执行表情。')
        last_level = time.monotonic()
        total_frames = energy = peak = clips = 0
        last_text = time.monotonic()
        try:
            while not stop.is_set():
                if control:
                    decision = control.tick(time.monotonic())
                    if decision:
                        channel.submit(decision.command, decision.reason)
                try:
                    at, pcm = frames.get(timeout=0.2)
                except queue.Empty:
                    continue
                if time.monotonic()-at > 0.5:
                    raise ProtocolError('音频已过期超过0.5秒：电脑处理延迟过大，已停止')
                samples = struct.unpack('<320h', pcm)
                peak = max(peak, max(abs(x) for x in samples))
                energy += sum(x*x for x in samples)
                clips += sum(abs(x) >= 32760 for x in samples)
                total_frames += 1
                for kind, text in recognizer.feed(pcm):
                    out(kind, text)
                    if kind in ('临时','最终'): last_text = time.monotonic()
                    if control:
                        route_result(kind, text, control, channel.submit, out,
                                     time.monotonic(), stopped=stop.is_set())
                now = time.monotonic()
                if now-last_level >= 2:
                    rms = math.sqrt(energy/max(1,total_frames*320))
                    out('音频', f'连续帧={reader.parser.frames} MIC{args.mic} peak={peak} rms={rms:.0f} 削波={clips} 队列={frames.qsize()}')
                    if now-last_text >= 8:
                        out('状态', '持续收到音频，但最近尚无中文结果；查看电平，尝试正常说完整句子。')
                        last_text = now
                    last_level = now; total_frames = energy = peak = clips = 0
        except KeyboardInterrupt:
            out('停止', '正在关闭板载麦克风。')
            stop.set()
        finally:
            stop.set()
            reader.join(timeout=2)
            if reader.is_alive():
                out('异常', '串口线程未及时退出；设备心跳超时后会关闭采音。')
        if reader.error:
            raise ProtocolError(str(reader.error))
        for kind, text in recognizer.finish():
            out(kind, text)
            if control: out('忽略', '程序已停止，结束时补出的文字不执行指令')
    out('停止', '串口已关闭，未保存录音或转录；此为电脑端ASR结果。')


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\n已取消。')
    except Exception as error:
        print(f'[异常] {error}', file=sys.stderr)
        raise SystemExit(1)
