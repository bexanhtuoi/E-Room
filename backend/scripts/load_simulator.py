"""Mo phong user that lien tuc de Grafana co so lieu that.

Hanh vi 1 user ao: xem list rooms -> vao phong (join) -> doc chat ->
gui 1-3 tin chat -> thi thoang hoi @ai / cham diem -> roi phong (leave).
Lap lai cho den khi het --minutes (0 = chay mai den khi Ctrl+C).

Khong cham diem that (ton CPU), khong goi @ai mac dinh (ton quota OpenRouter).
Bat khi can: --with-ai (hiem), --bad-rate tao them loi 4xx cho panel Error.

Usage (from backend/):
    uv run python scripts/load_simulator.py --users 3 --interval 3 --minutes 10
"""

from __future__ import annotations

import argparse
import random
import time
import uuid

import httpx

CHAT_LINES = [
    "Hello everyone!",
    "How do you pronounce this word?",
    "I think travel is fun, what about you?",
    "Can you repeat that slowly?",
    "My favorite topic is food and cooking.",
    "I went to the market yesterday.",
    "She doesn't like coffee, me neither.",
    "What did you do last weekend?",
    "Let's practice introducing ourselves.",
    "How long have you been learning English?",
]

AI_QUESTIONS = [
    "@ai how do I pronounce the word think?",
    "@ai correct my sentence: Yesterday I go to market.",
    "@ai give me a topic to talk about travel.",
]


def make_client(base: str) -> httpx.Client:
    return httpx.Client(base_url=base, timeout=30.0)


def ensure_user(client: httpx.Client, tag: int) -> httpx.Client:
    email = f"sim_{tag}_{uuid.uuid4().hex[:6]}@gmail.com"
    password = "Simpass123!"

    client.post(
        "/api/v1/auth/register",
        json={"full_name": f"Sim User {tag}", "email": email, "password": password},
    )
    resp = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    resp.raise_for_status()
    return client


def pick_room(client: httpx.Client) -> int | None:
    try:
        rooms = client.get("/api/v1/rooms/", params={"public_only": "true"}).json()
    except Exception:
        return None

    if not rooms:
        return None

    room = random.choice(rooms)
    return room.get("id")


def user_loop(base: str, tag: int, interval: float, stop_at: float, with_ai: bool, bad_rate: float) -> None:
    client = make_client(base)

    try:
        ensure_user(client, tag)
    except Exception as error:
        print(f"[sim-{tag}] register/login failed: {error}")
        return

    print(f"[sim-{tag}] online")

    while stop_at <= 0 or time.time() < stop_at:
        try:
            room_id = pick_room(client)

            if room_id is None:
                time.sleep(interval)
                continue

            client.get(f"/api/v1/rooms/{room_id}")
            client.post(f"/api/v1/rooms/{room_id}/join")
            client.get("/api/v1/messages/", params={"room_id": room_id, "limit": 30})

            for _ in range(random.randint(1, 3)):
                if with_ai and random.random() < 0.15:
                    text = random.choice(AI_QUESTIONS)
                else:
                    text = random.choice(CHAT_LINES)
                client.post("/api/v1/messages/", json={"room_id": room_id, "text": text})
                time.sleep(random.uniform(1.0, 3.0))

            if random.random() < bad_rate:
                client.get("/api/v1/rooms/999999999")

            client.get(f"/api/v1/rooms/{room_id}/speech-logs/summary")
            client.post(f"/api/v1/rooms/{room_id}/leave")
        except Exception as error:
            print(f"[sim-{tag}] action failed (tiep tuc): {str(error)[:100]}")

        time.sleep(random.uniform(interval * 0.5, interval * 1.5))

    print(f"[sim-{tag}] done")


def main() -> None:
    parser = argparse.ArgumentParser(description="E-Room user simulator")
    parser.add_argument("--base", default="http://localhost:8000")
    parser.add_argument("--users", type=int, default=3)
    parser.add_argument("--interval", type=float, default=3.0)
    parser.add_argument("--minutes", type=float, default=0.0)
    parser.add_argument("--with-ai", action="store_true")
    parser.add_argument("--bad-rate", type=float, default=0.05)
    args = parser.parse_args()

    stop_at = time.time() + args.minutes * 60 if args.minutes > 0 else 0

    print(f"simulator: users={args.users} base={args.base} minutes={args.minutes or 'vo han'}")

    import threading

    threads = [
        threading.Thread(
            target=user_loop,
            args=(args.base, i, args.interval, stop_at, args.with_ai, args.bad_rate),
            daemon=True,
        )
        for i in range(args.users)
    ]

    for thread in threads:
        thread.start()

    try:
        while any(thread.is_alive() for thread in threads):
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("stopped")


if __name__ == "__main__":
    main()
