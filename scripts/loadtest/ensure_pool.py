import json
import sys
import time

import httpx

BASE = "http://localhost:8000"
POOL_FILE = "scripts/loadtest/.tokens.json"

want = int(sys.argv[1]) if len(sys.argv) > 1 else 50

try:
    saved = json.load(open(POOL_FILE, encoding="utf-8"))
except (OSError, ValueError):
    saved = {}

client = httpx.Client(base_url=BASE, timeout=30)
tokens = []

for i in range(1, want + 1):
    email = f"k6_{i}@gmail.com"

    if email in saved:
        probe = client.get("/api/v1/users/me", headers={"Cookie": f"access_token={saved[email]}"})

        if probe.status_code == 200:
            tokens.append(saved[email])
            continue

        del saved[email]

    resp = client.post("/api/v1/auth/login", data={"username": email, "password": "K6pass123!"})

    if resp.status_code != 200:
        client.post(
            "/api/v1/auth/register",
            json={"full_name": f"K6 {i}", "email": email, "password": "K6pass123!"},
        )
        time.sleep(1.0)
        resp = client.post("/api/v1/auth/login", data={"username": email, "password": "K6pass123!"})
        resp.raise_for_status()

    token = resp.cookies.get("access_token")
    saved[email] = token
    tokens.append(token)
    json.dump(saved, open(POOL_FILE, "w", encoding="utf-8"))
    time.sleep(2.0)

print(f"pool ok: {len(tokens)}/{want}")
