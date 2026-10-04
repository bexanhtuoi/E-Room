import httpx

BASE = "http://localhost:8000"

client = httpx.Client(base_url=BASE, timeout=15)
client.post(
    "/api/v1/auth/register",
    json={"full_name": "Room Picker", "email": "picker@gmail.com", "password": "Pickpass123!"},
)
client.post("/api/v1/auth/login", data={"username": "picker@gmail.com", "password": "Pickpass123!"})

rooms = client.get("/api/v1/rooms/", params={"public_only": "true"}).json()

print(rooms[0]["id"] if rooms else "")
