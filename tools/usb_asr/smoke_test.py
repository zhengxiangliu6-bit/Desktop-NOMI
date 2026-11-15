"""Public fixture SOFTWARE smoke test; not a physical board or Windows test."""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import tarfile
import urllib.request
import wave
from protocol import FrameParser,checksum
from recognizer import ChineseRecognizer
from setup_model import ROOT,verify_model


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, help='Existing pinned public model archive; otherwise download it')
    args=parser.parse_args()
    lock=json.loads((ROOT/'model.lock.json').read_text(encoding='utf-8'))
    if args.archive: archive=args.archive.read_bytes()
    else:
        with urllib.request.urlopen(lock['url'],timeout=60) as source: archive=source.read(lock['archive_bytes']+1)
    assert len(archive)==lock['archive_bytes']
    assert hashlib.sha256(archive).hexdigest()==lock['archive_sha256']
    with tarfile.open(fileobj=io.BytesIO(archive),mode='r:bz2') as bundle:
        member=next(m for m in bundle.getmembers() if m.name.lstrip('./')==lock['model']+'/test_wavs/0.wav')
        wav=bundle.extractfile(member).read()
    assert hashlib.sha256(wav).hexdigest()==lock['public_fixture_sha256']
    with wave.open(io.BytesIO(wav)) as w:
        assert (w.getframerate(),w.getnchannels(),w.getsampwidth())==(16000,1,2)
        raw=w.readframes(w.getnframes())
    recognizer=ChineseRecognizer(verify_model())
    frames=FrameParser(1); final=[]
    for seq, offset in enumerate(range(0,len(raw),640)):
        pcm=raw[offset:offset+640].ljust(640,b'\0')
        line=f'@NOMI1 00000001 {seq:08x} 1 {checksum(1,seq,1,pcm):08x} '.encode()+base64.b64encode(pcm)
        for kind,text in recognizer.feed(frames.parse(line)):
            if kind=='最终': final.append(text)
    final.extend(text for kind,text in recognizer.finish() if kind=='最终')
    text=''.join(final)
    assert sum('\u4e00' <= char <= '\u9fff' for char in text)>=4, 'No actual Chinese decoding result'
    print('PUBLIC_FIXTURE_SOFTWARE_TEST_OK frames=',frames.frames,'Chinese_chars=',len(text))


if __name__=='__main__':main()
