"""Fetch the single external source dependency at a verified revision (Git required)."""
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
LVGL_SHA = "85aa60d18b3d5e5588d7b247abf90198f07c8a63"
destination = ROOT / "components" / "lvgl"
if not destination.exists():
    subprocess.run([
        "git", "clone", "--depth", "1", "--branch", "v9.5.0",
        "https://github.com/lvgl/lvgl.git", str(destination),
    ], check=True)
actual = subprocess.check_output(["git", "-C", str(destination), "rev-parse", "HEAD"], text=True).strip()
if actual != LVGL_SHA:
    raise SystemExit(f"LVGL revision mismatch: expected {LVGL_SHA}, found {actual}")
if subprocess.check_output(["git", "-C", str(destination), "status", "--porcelain"], text=True).strip():
    raise SystemExit("LVGL checkout contains changes; use a clean pinned checkout")
print(f"LVGL 9.5.0 verified: {actual}")
