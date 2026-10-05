import sys

rooms = [r for r in sys.argv[1].split(",") if r.strip()]
speakers = [s for s in sys.argv[2].split(",") if s.strip()] or ["1"]

for i, room in enumerate(rooms):
    print(f"{room} {speakers[i % len(speakers)]}")
