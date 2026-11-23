"""Derive a pinned PUBLIC Espressif diagnostic fixture; never uses personal audio."""
import hashlib,json,pathlib,re,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1]
PATH='test_apps/esp-sr/main/samples/da_kai_kong_tiao.h'
HEADER='1ac479d217703396d681f352e969268a6c105b563f24638e8a7ca4f8c56b8d68'
PCM='4725f6b9ababad72eb66459f756e10b838f9bc17ddc0ab2c92e7f46ca7e83f9d'
def main():
    repo=ROOT/'.deps/esp-sr'
    expected=next(d['sha'] for d in json.loads((ROOT/'dependencies.lock.json').read_text(encoding='utf-8'))['dependencies'] if d['name']=='esp-sr')
    source=subprocess.check_output(['git','-C',str(repo),'show',expected+':'+PATH])
    if hashlib.sha256(source).hexdigest()!=HEADER:raise SystemExit('Public fixture header hash mismatch')
    pcm=bytes(int(x,16) for x in re.findall(rb'0x([0-9a-fA-F]{2})',source))
    if hashlib.sha256(pcm).hexdigest()!=PCM:raise SystemExit('Public fixture PCM hash mismatch')
    target=ROOT/'.generated/official_command.pcm';target.parent.mkdir(exist_ok=True)
    if not target.exists() or target.read_bytes()!=pcm:target.write_bytes(pcm)
    print('Verified public official-command fixture:',len(pcm),'bytes; not user audio')
if __name__=='__main__':main()
