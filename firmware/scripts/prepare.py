"""Fetch official dependencies and verify commits/model hashes; never flash."""
import hashlib
import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
LOCK = json.loads((ROOT / "dependencies.lock.json").read_text(encoding="utf-8"))


def git(*args):
    return subprocess.check_output(["git", *map(str, args)], text=True).strip()


for dep in LOCK["dependencies"]:
    destination = ROOT / dep["path"]
    if not destination.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        git("init", destination)
        git("-C", destination, "remote", "add", "origin", dep["url"])
        git("-C", destination, "config", "core.autocrlf", "false")
        if dep.get("sparse"):
            git("-C", destination, "config", "remote.origin.promisor", "true")
            git("-C", destination, "config", "remote.origin.partialclonefilter", "blob:none")
            git("-C", destination, "fetch", "--depth", "1", "--filter=blob:none", "origin", dep["ref"])
            git("-C", destination, "sparse-checkout", "set", *dep["sparse"])
        else:
            git("-C", destination, "fetch", "--depth", "1", "origin", dep["ref"])
        git("-C", destination, "checkout", "--detach", "FETCH_HEAD")
    actual = git("-C", destination, "rev-parse", "HEAD")
    if actual != dep["sha"]:
        raise SystemExit(f"{dep['name']}: revision mismatch: {actual}")
    if git("-C", destination, "status", "--porcelain", "--untracked-files=normal"):
        raise SystemExit(f"{dep['name']}: local changes; preserve them and use a clean checkout")
    print(f"Verified {dep['name']} {dep['version']}: {actual}")

for name, expected in LOCK["benchmark"]["files"].items():
    path = ROOT / ".deps/esp-sr/model/wakenet_model" / LOCK["benchmark"]["model"] / name
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise SystemExit(f"Benchmark model hash mismatch: {name}")
print("Benchmark is Xiaoai Tongxue ONLY; Xiaomi Tongxue model is unavailable.")
