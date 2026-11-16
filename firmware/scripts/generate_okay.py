"""Development-only fixed asset synthesis. Requires espeakng-loader==0.2.4 and FFmpeg.
Never used by the firmware or Windows runtime; text is the fixed literal 好的.
The checked-in metadata/hash is authoritative; regeneration changes require review.
"""
import ctypes as C,wave,pathlib,tempfile,subprocess
import espeakng_loader
lib=espeakng_loader.load_library()
lib.espeak_Initialize.argtypes=[C.c_int,C.c_int,C.c_char_p,C.c_int]
lib.espeak_SetVoiceByName.argtypes=[C.c_char_p]
lib.espeak_SetParameter.argtypes=[C.c_int,C.c_int,C.c_int]
callback=C.CFUNCTYPE(C.c_int,C.POINTER(C.c_short),C.c_int,C.c_void_p)
chunks=[]
@callback
def receive(samples,count,events):
 if samples and count:chunks.append(C.string_at(samples,count*2))
 return 0
lib.espeak_SetSynthCallback.argtypes=[callback]
root=str(pathlib.Path(espeakng_loader.get_data_path()).parent).encode()
rate=lib.espeak_Initialize(2,0,root,0)
print('rate',rate,'voice_result',lib.espeak_SetVoiceByName(b'cmn'))
lib.espeak_SetSynthCallback(receive)
lib.espeak_SetParameter(1,150,0)
text='好的'.encode()
lib.espeak_Synth.argtypes=[C.c_void_p,C.c_size_t,C.c_uint,C.c_int,C.c_uint,C.c_uint,C.c_void_p,C.c_void_p]
buf=C.create_string_buffer(text)
print('synth',lib.espeak_Synth(buf,len(text)+1,0,1,0,1,None,None))
temp=tempfile.TemporaryDirectory()
source=pathlib.Path(temp.name)/'okay.wav'
with wave.open(str(source),'wb') as w:
 w.setnchannels(1);w.setsampwidth(2);w.setframerate(rate);w.writeframes(b''.join(chunks))
print('samples',sum(len(x) for x in chunks)//2)

output=pathlib.Path(__file__).resolve().parents[1]/'components/nomi_audio/assets/okay.pcm'
subprocess.run(['ffmpeg','-y','-i',str(source),'-ar','16000','-ac','1','-af','loudnorm=I=-23:TP=-6:LRA=5','-f','s16le',str(output)],check=True)
temp.cleanup()
