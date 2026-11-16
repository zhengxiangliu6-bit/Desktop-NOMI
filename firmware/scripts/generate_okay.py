"""Development-only neural synthesis of fixed 好的; never runs on ESP32/Windows control.
Install sherpa-onnx==2.0.1 and FFmpeg 7.1.5 in a development environment.
Download/extract the model URL in assets/okay.json separately, then pass --model-dir.
No runtime network, cloud TTS, microphone, arbitrary text, or voice cloning.
Inference can vary; checked-in PCM + metadata SHA256 are the authoritative release asset.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import wave


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model-dir',type=Path,required=True)
    args=parser.parse_args()
    import numpy as np
    import sherpa_onnx as sherpa
    root=Path(__file__).resolve().parents[1]/'components/nomi_audio/assets'
    meta=json.loads((root/'okay.json').read_text(encoding='utf-8'))
    gen=meta['generator'];model=args.model_dir/'model.onnx'
    if hashlib.sha256(model.read_bytes()).hexdigest()!=gen['model_sha256']:
        raise SystemExit('Model does not match recorded release SHA256')
    vits=sherpa.OfflineTtsVitsModelConfig(model=str(model),lexicon=str(args.model_dir/'lexicon.txt'),
                                        tokens=str(args.model_dir/'tokens.txt'),dict_dir=str(args.model_dir/'dict'))
    tts=sherpa.OfflineTts(sherpa.OfflineTtsConfig(model=sherpa.OfflineTtsModelConfig(vits=vits,num_threads=2,provider='cpu')))
    clip=tts.generate('好的。',sid=0,speed=1.0)
    with tempfile.TemporaryDirectory() as temp:
        source=Path(temp)/'okay.wav';output=Path(temp)/'okay.pcm'
        with wave.open(str(source),'wb') as w:
            w.setnchannels(1);w.setsampwidth(2);w.setframerate(clip.sample_rate)
            w.writeframes((np.asarray(clip.samples).clip(-1,1)*32767).astype('<i2').tobytes())
        subprocess.run(['ffmpeg','-y','-i',str(source),'-af','loudnorm=I=-23:TP=-6:LRA=5',
                        '-ar','16000','-ac','1','-f','s16le',str(output)],check=True)
        pcm=output.read_bytes()
    if not 0<len(pcm)<=32000 or len(pcm)%2:raise SystemExit('Fixed reply must be <=1 second PCM16 mono')
    meta.update(samples=len(pcm)//2,bytes=len(pcm),sha256=hashlib.sha256(pcm).hexdigest())
    (root/'okay.pcm').write_bytes(pcm)
    (root/'okay.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Generated fixed neural reply; review audio and metadata before committing:',meta['sha256'])


if __name__=='__main__':main()
