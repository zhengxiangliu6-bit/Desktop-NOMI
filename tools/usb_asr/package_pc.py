"""Package a source-only PC update; never include models, recordings or a Python env."""
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
# Explicit allowlist: no recursive traversal into caches, user files, models or virtualenv.
FILES=['transcribe.py','protocol.py','recognizer.py','setup_model.py','smoke_test.py',
       'voice_control.py','command_channel.py','model.lock.json','requirements.txt',
       'start.cmd','start_control.cmd','setup.cmd','README.md']


def main():
    def git(*args):
        return subprocess.check_output(['git','-c',f'safe.directory={REPO}',*args],cwd=REPO,text=True).strip()
    files={"pc/"+name:ROOT/name for name in FILES}
    files['pc/VOICE_CONTROL_GUIDE.md']=REPO/'docs/PC_VOICE_CONTROL.md'
    manifest={'pc_version':'0.4.1','compatible_firmware':'0.4.0 usb_asr',
              'source_commit':git('rev-parse','HEAD'),'source_dirty':bool(git('status','--porcelain')),
              'sha256':{name:hashlib.sha256(path.read_bytes()).hexdigest() for name,path in files.items()}}
    target=ROOT/'dist/desktop-nomi-pc-voice-control-v0.4.1.zip'
    target.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
        for name,path in files.items():z.write(path,name)
        z.writestr('pc/pc-update-manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(target)


if __name__=='__main__':main()
