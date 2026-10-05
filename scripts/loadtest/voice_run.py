import subprocess
import sys
import time

REPO = "C:/Users/PC/Downloads/E-Room"
LK = REPO + "/scripts/loadtest/bin/lk.exe"

rooms = [r for r in sys.argv[1].split(",") if r.strip()]
speakers = [s for s in sys.argv[2].split(",") if s.strip()] or ["1"]
duration = sys.argv[3] if len(sys.argv) > 3 else "5m"
secret = sys.argv[4] if len(sys.argv) > 4 else ""

procs = []

for i, room in enumerate(rooms):
    count = speakers[i % len(speakers)]
    log = open(f"{REPO}/lk-voice-{room}.log", "w", encoding="utf-8")
    procs.append(
        subprocess.Popen(
            [
                LK, "load-test",
                "--url", "ws://localhost:7880",
                "--api-key", "eroom-livekit",
                "--api-secret", secret,
                "--room", room,
                "--audio-publishers", count,
                "--simulate-speakers",
                "--duration", duration,
                "--num-per-second", "2",
            ],
            stdout=log,
            stderr=subprocess.STDOUT,
        )
    )
    print(f"lk room {room}: {count} speakers", flush=True)

for proc in procs:
    proc.wait()

print("voice done")
