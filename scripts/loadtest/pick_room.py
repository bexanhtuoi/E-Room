import sys

import httpx

BASE = "http://localhost:8000"

client = httpx.Client(base_url=BASE, timeout=15)
reg = client.post(
    "/api/v1/auth/register",
    json={"full_name": "Room Picker", "email": "picker@gmail.com", "password": "Pickpass123!"},
)
login = client.post("/api/v1/auth/login", data={"username": "picker@gmail.com", "password": "Pickpass123!"})

if login.status_code != 200:
    print(f"picker auth failed: register={reg.status_code} login={login.status_code}")
    print("")

    raise SystemExit(1)

if len(sys.argv) > 2 and sys.argv[1] == "leave":
    client.post(f"/api/v1/rooms/{sys.argv[2]}/leave")
    print("left")

    raise SystemExit

want_rooms = int(sys.argv[1]) if len(sys.argv) > 1 else 1
room_size = int(sys.argv[2]) if len(sys.argv) > 2 else 6

rooms = client.get("/api/v1/rooms/", params={"public_only": "true"}).json()
ids = []

for i in range(1, want_rooms + 1):
    name = f"Load Voice {i}"
    voice = next((r for r in rooms if r.get("name") == name), None)

    if voice is None:
        voice = client.post(
            "/api/v1/rooms/",
            json={"name": name, "max_participants": room_size},
        ).json()

    room_id = voice["id"]
    client.post(f"/api/v1/rooms/{room_id}/join")
    ids.append(str(room_id))

print(",".join(ids))
