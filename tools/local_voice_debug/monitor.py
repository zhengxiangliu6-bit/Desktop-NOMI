"""Display ESP32-local results and receive raw/AFE PCM. No PC ASR, cloud or default recordings."""
import argparse,base64,binascii,struct,time,secrets,wave
from pathlib import Path

def checksum(token,seq,ch,payload):
    value=2166136261
    for byte in struct.pack('<IIB',token,seq,ch)+payload:value=((value^byte)*16777619)&0xffffffff
    return value

class TraceParser:
    def __init__(self,token):self.token=token;self.sequences={1:0,2:0};self.frames={1:0,2:0}
    def parse(self,line):
        if not line.startswith(b'@NTRC1 '):return None
        parts=line.strip().split()
        try:
            if len(parts)>=2 and int(parts[1],16)!=self.token:return None
            if len(parts)!=7:raise ValueError('field count')
            _,token,seq,ch,flags,digest,payload=parts
            token,seq,ch,flags,digest=int(token,16),int(seq,16),int(ch),int(flags),int(digest,16)
            if ch not in (1,2) or flags not in (0,1) or not 0<=seq<=0xffffffff:raise ValueError('header')
            pcm=base64.b64decode(payload,validate=True)
            if len(pcm)!=640 or checksum(token,seq,ch,bytes([flags])+pcm)!=digest:raise ValueError('checksum/length')
            if seq!=self.sequences[ch]:raise ValueError(f'channel {ch} frame gap {self.sequences[ch]} -> {seq}')
        except (ValueError,binascii.Error) as error:raise ValueError('串口音频帧损坏或丢失：'+str(error)) from error
        self.sequences[ch]=(seq+1)&0xffffffff;self.frames[ch]+=1
        return ch,flags,pcm

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',default='COM3')
    parser.add_argument('--seconds',type=float,default=20)
    parser.add_argument('--threshold',type=int,choices=range(30,96),metavar='30..95')
    parser.add_argument('--record-dir',type=Path,help='Explicit optional WAV recording folder; no files otherwise')
    args=parser.parse_args()
    if not 1<=args.seconds<=600:parser.error('seconds must be 1..600')
    import serial
    print('[说明] 音频和有限指令识别都在ESP32运行；电脑只接收。此工具没有ASR模型，不上传音频。',flush=True)
    print('[说明] CH1=麦克风原始PCM，CH2=AFE输出(正常识别期间含恢复的VAD开头)。模型未命中时没有完整中文转录。',flush=True)
    print('[录音] '+('显式保存两个WAV到 '+str(args.record_dir) if args.record_dir else '不保存音频或文字'),flush=True)
    input('先关闭miniterm/旧PC语音程序；按Enter开始串口调试，Ctrl+C停止：')
    token=secrets.randbelow(0xffffffff)+1;frames=TraceParser(token);files={};buffer=bytearray()
    guarded={1:0,2:0};peaks={1:0,2:0};energies={1:0,2:0};samples={1:0,2:0};last=0;next_report=0;candidates=0;reported_candidates=0
    with serial.Serial(args.port,115200,timeout=.05,write_timeout=.5) as port:
        try:
            if args.record_dir:
                args.record_dir.mkdir(parents=True,exist_ok=True)
                # Do not overwrite an earlier diagnostic recording.
                for ch,name in [(1,'raw-mic1.wav'),(2,'afe-output.wav')]:
                    handle=(args.record_dir/name).open('xb')
                    try:w=wave.open(handle,'wb');w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000)
                    except BaseException:handle.close();raise
                    files[ch]=(w,handle)
            port.write(b'status\r\n')
            if args.threshold is not None:port.write(f'voice threshold {args.threshold}\r\n'.encode())
            port.write(f'trace on {token:08x}\r\n'.encode())
            start=time.monotonic()
            while time.monotonic()-start<args.seconds:
                now=time.monotonic()
                if now-last>=.5:port.write(f'trace ping {token:08x}\r\n'.encode());last=now
                buffer.extend(port.read(max(1,port.in_waiting)))
                if len(buffer)>65536:raise ValueError('串口缺少换行/接收积压，停止调试而不伪造音频')
                while b'\n' in buffer:
                    line,_,tail=buffer.partition(b'\n');buffer[:]=tail
                    marker=line.find(b'@NTRC1 ')
                    if marker>=0:
                        if marker:print('[设备] '+line[:marker].decode('utf-8',errors='replace'),flush=True)
                        parsed=frames.parse(bytes(line[marker:]))
                        if parsed:
                            ch,flags,pcm=parsed;guarded[ch]+=flags;values=struct.unpack('<320h',pcm)
                            peaks[ch]=max(peaks[ch],max(map(abs,values)));energies[ch]+=sum(x*x for x in values);samples[ch]+=320
                            if ch in files:files[ch][0].writeframesraw(pcm)
                    elif b'@NRES1 ' in line:
                        candidates+=1
                        print('[ESP32本地候选] '+line[line.index(b'@NRES1 ')+7:].decode('utf-8',errors='replace').strip(),flush=True)
                    elif line.strip():print('[ESP32] '+line.decode('utf-8',errors='replace').strip(),flush=True)
                if now>=next_report:
                    for ch,label in [(1,'识别前 MIC1'),(2,'AFE输出')]:
                        rms=int((energies[ch]/samples[ch])**.5) if samples[ch] else 0
                        print(f'[音频 {label}] 有效帧={frames.frames[ch]} peak={peaks[ch]} rms={rms} 保护帧={guarded[ch]}',flush=True)
                        peaks[ch]=energies[ch]=samples[ch]=guarded[ch]=0
                    if candidates==reported_candidates:print('[本地识别] 本秒未收到配置指令候选；不生成虚构转录。',flush=True)
                    reported_candidates=candidates;next_report=now+1
        finally:
            try:port.write(b'trace off\r\nstatus\r\n')
            except serial.SerialException:pass
            try:
                # Drain final model/resource status after audio transport has stopped.
                end=time.monotonic()+1
                while time.monotonic()<end:
                    line=port.readline()
                    if line and b'@NTRC1 ' not in line:print('[ESP32] '+line.decode('utf-8',errors='replace').strip(),flush=True)
            except serial.SerialException:pass
            finally:
                for w,handle in files.values():
                    try:w.close()
                    finally:handle.close()
    print('[结束] 串口音频传输关闭，设备本地识别继续运行。',flush=True)

if __name__=='__main__':
    try:main()
    except KeyboardInterrupt:print('\n[停止] 用户结束调试。')
    except (ValueError,OSError) as error:raise SystemExit('[错误] '+str(error))
