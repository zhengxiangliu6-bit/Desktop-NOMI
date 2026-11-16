"""Import a user-selected fixed 好的 WAV into firmware. No network, TTS or flashing."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import wave

ROOT=Path(__file__).resolve().parents[1]


def read_wav(source):
    with wave.open(str(source),'rb') as wav:
        if (wav.getnchannels(),wav.getsampwidth(),wav.getframerate(),wav.getcomptype())!=(1,2,16000,'NONE'):
            raise ValueError('Use uncompressed PCM16 WAV, mono, 16000Hz; convert first, do not rename an MP3')
        count=wav.getnframes()
        if not 1600<=count<=48000:raise ValueError('Duration must be 0.1 to 3 seconds (suggest 0.3 to 2 for 好的)')
        pcm=wav.readframes(count)
    if len(pcm)!=count*2:raise ValueError('Truncated WAV data')
    values=struct.unpack('<'+'h'*count,pcm)
    peak=max(abs(x) for x in values)
    if peak==0:raise ValueError('Silent audio')
    if peak>=32767:raise ValueError('Audio is digitally clipped; export a quieter source')
    return pcm


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input',type=Path)
    parser.add_argument('--source',default='User-selected fixed reply audio')
    parser.add_argument('--license-note',default='Supplied for local project playback; no public redistribution license asserted.')
    args=parser.parse_args()
    pcm=read_wav(args.input)
    folder=ROOT/'components/nomi_audio/assets'
    meta={'text':'好的','format':'s16le','sample_rate':16000,'channels':1,'samples':len(pcm)//2,
          'bytes':len(pcm),'sha256':hashlib.sha256(pcm).hexdigest(),
          'generator':{'type':'user_selected_fixed_asset','source':args.source,
                       'source_wav_sha256':hashlib.sha256(args.input.read_bytes()).hexdigest(),
                       'license_note':args.license_note},
          'provenance':'Explicitly selected fixed reply; content and source rights supplied by the user. No microphone capture performed.'}
    # Original paths and the source WAV are not copied into the repository or manifest.
    (folder/'okay.pcm').write_bytes(pcm)
    (folder/'okay.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (folder/'NOTICE.md').write_text('# User-selected fixed reply\n\nSource: '+args.source+'\n\n'+args.license_note+
        '\n\nImported by firmware/scripts/import_reply.py as PCM16LE mono16000Hz. Only the fixed clip is embedded; no runtime TTS. '+
        'See okay.json for content label/format/sample count/hash. The label is user-declared, not proof of speech content. '+
        'The bundled MeloTTS-LICENSE.txt describes the previous stock asset, not this replacement.\n',encoding='utf-8')
    print(f'Imported {len(pcm)//2/16000:.3f}s / {len(pcm)} bytes. Preview, build and flash again. No Git upload or flashing performed.')


if __name__=='__main__':main()
