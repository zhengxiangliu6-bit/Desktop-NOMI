"""Local serial observation only; no audio capture files, upload, flash or erase."""
import argparse
import re
import time
import serial

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--port", required=True)
p.add_argument("--minutes", type=float, default=30)
a = p.parse_args()
if not 0 < a.minutes <= 120:
    p.error("minutes must be in (0,120]")
end = time.monotonic() + a.minutes * 60
last_request = 0
previous_runtime = {}
previous_uptime = None
with serial.Serial(a.port, 115200, timeout=0.2) as s:
    # No reset commands sent. Windows/USB may still toggle control lines on port open.
    while time.monotonic() < end:
        now = time.monotonic()
        if now - last_request >= 60:
            s.write(b"status\r\n")
            last_request = now
        line = s.readline(2048).decode("utf-8", errors="replace").strip()
        if not line:
            continue
        if any(word in line for word in ("nomi:", "wake:", "nomi_audio:", "voice:", "Guru Meditation", "rst:")):
            print(line, flush=True)
        m = re.search(r"uptime_ms=(\d+)", line)
        if m:
            uptime = int(m[1])
            if previous_uptime is not None and uptime < previous_uptime:
                print("WARNING: uptime went backwards; possible reboot")
            previous_uptime = uptime
        m = re.search(r"task=(\w+) .*runtime_us=(\d+)", line)
        if m:
            task, runtime = m[1], int(m[2])
            if task in previous_runtime:
                before_time, before_runtime = previous_runtime[task]
                # 32-bit runtime counter wraps; result is share of ONE core, not total chip utilization.
                delta = (runtime - before_runtime) & 0xffffffff
                print(f"{task}: {delta / ((now-before_time)*1e6) * 100:.1f}% of one core (observed interval)")
            previous_runtime[task] = now, runtime
print("Observation interval complete. Review logs/face/wake tests; this alone is NOT a hardware PASS.")
