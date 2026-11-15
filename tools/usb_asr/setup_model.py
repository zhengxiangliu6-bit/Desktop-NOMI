"""Download fixed public model once; no microphone, audio upload, or paid API."""
import hashlib
import json
from pathlib import Path
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parent


def verify_model(root=ROOT):
    lock = json.loads((root/'model.lock.json').read_text(encoding='utf-8'))
    model = root/'models'/lock['model']
    for name, digest in lock['files'].items():
        path = model/name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError(f'模型缺失或校验失败：{name}；请重新运行 setup.cmd')
    return model


def main():
    lock = json.loads((ROOT/'model.lock.json').read_text(encoding='utf-8'))
    try:
        print('模型校验通过：', verify_model())
        return
    except ValueError:
        pass
    target = ROOT/'models'/lock['model']
    target.mkdir(parents=True, exist_ok=True)
    archive = ROOT/'models'/'download.partial'
    print('下载固定中文模型，约21 MB；仅下载模型，不上传任何音频。')
    try:
        with urllib.request.urlopen(lock['url'], timeout=60) as source, archive.open('wb') as output:
            total = 0
            while chunk := source.read(1024*1024):
                total += len(chunk)
                if total > lock['archive_bytes']:
                    raise ValueError('模型下载超出预期大小')
                output.write(chunk)
        if total != lock['archive_bytes'] or hashlib.sha256(archive.read_bytes()).hexdigest() != lock['archive_sha256']:
            raise ValueError('模型压缩包校验失败，请检查网络后重试')
        # Extract only named regular model files. Never extract arbitrary paths, links or audio samples.
        with tarfile.open(archive, 'r:bz2') as bundle:
            for name, digest in lock['files'].items():
                members = [m for m in bundle.getmembers() if m.name.lstrip('./') == lock['model']+'/'+name]
                if len(members) != 1 or not members[0].isfile() or members[0].size > 40*1024*1024:
                    raise ValueError('模型压缩包结构错误')
                data = bundle.extractfile(members[0]).read()
                if hashlib.sha256(data).hexdigest() != digest:
                    raise ValueError('解压模型文件校验失败')
                (target/name).write_bytes(data)
        print('模型已就绪：', verify_model())
    finally:
        archive.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
