import httpx

BASE = "http://localhost:8000"

client = httpx.Client(base_url=BASE, timeout=15)
client.post(
    "/api/v1/auth/register",
    json={"full_name": "Room Picker", "email": "picker@gmail.com", "password": "Pickpass123!"},
)
client.post("/api/v1/auth/login", data={"username": "picker@gmail.com", "password": "Pickpass123!"})

rooms = client.get("/api/v1/rooms/", params={"public_only": "true"}).json()

voice = next((r for r in rooms if r.get("name") == "Load Voice"), None)

if voice is None:
    voice = client.post(
        "/api/v1/rooms/",
        json={"name": "Load Voice", "max_participants": 6},
    ).json()

room_id = voice["id"]
client.post(f"/api/v1/rooms/{room_id}/join")
print(room_id)
