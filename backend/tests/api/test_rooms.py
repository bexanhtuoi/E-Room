from __future__ import annotations

import jwt as pyjwt
from fastapi.testclient import TestClient

from app.config import settings
from app.integration.redis import delete as redis_delete, sadd, smembers
from tests.conftest import make_user, switch_to


def create_room(client: TestClient, name: str, topic: str | None = None) -> dict:
    response = client.post("/api/v1/rooms/", json={"name": name, "topic": topic, "max_participants": 5})
    assert response.status_code == 201, response.text
    return response.json()


class TestRoomCrud:
    def test_create_room_sets_host(self, client: TestClient, alice: dict):
        room = create_room(client, f"room-{alice['id']}-host", "Greetings")
        assert room["host_id"] == alice["id"]
        assert room["status"] == "idle"
        assert room["max_participants"] == 5

    def test_create_duplicate_name_returns_400(self, client: TestClient, alice: dict):
        name = f"dup-room-{alice['id']}"
        create_room(client, name)
        duplicate = client.post("/api/v1/rooms/", json={"name": name})
        assert duplicate.status_code == 400

    def test_list_and_count_rooms(self, client: TestClient, alice: dict):
        create_room(client, f"list-room-{alice['id']}")
        listed = client.get("/api/v1/rooms/?limit=50").json()
        names = [r["name"] for r in listed]
        assert f"list-room-{alice['id']}" in names
        assert client.get("/api/v1/rooms/count").json()["count"] >= 1

    def test_get_room_by_id_and_404(self, client: TestClient, alice: dict):
        room = create_room(client, f"get-room-{alice['id']}")
        fetched = client.get(f"/api/v1/rooms/{room['id']}").json()
        assert fetched["name"] == room["name"]
        assert client.get("/api/v1/rooms/999999").status_code == 404

    def test_update_by_host(self, client: TestClient, alice: dict):
        room = create_room(client, f"upd-room-{alice['id']}")
        updated = client.patch(f"/api/v1/rooms/{room['id']}", json={"topic": "New Topic", "status": "active"})
        assert updated.status_code == 200
        assert updated.json()["topic"] == "New Topic"
        assert updated.json()["status"] == "active"

    def test_update_by_non_host_returns_403(self, client: TestClient, alice: dict):
        room = create_room(client, f"guard-room-{alice['id']}")
        bob = make_user(client)
        switch_to(client, bob)
        response = client.patch(f"/api/v1/rooms/{room['id']}", json={"topic": "Hijack"})
        assert response.status_code == 403
        switch_to(client, alice)

    def test_delete_cascades_messages(self, client: TestClient, alice: dict):
        room = create_room(client, f"del-room-{alice['id']}")
        client.post("/api/v1/messages/", json={"room_id": room["id"], "text": "bye", "role": "user"})

        assert client.delete(f"/api/v1/rooms/{room['id']}").status_code == 200
        assert client.get(f"/api/v1/rooms/{room['id']}").status_code == 404
        assert client.get(f"/api/v1/messages/?room_id={room['id']}").json() == []


class TestLivekitToken:
    def test_token_contains_correct_claims(self, client: TestClient, alice: dict):
        room = create_room(client, f"token-room-{alice['id']}")
        response = client.post(f"/api/v1/rooms/{room['id']}/token")
        assert response.status_code == 200

        data = response.json()
        assert data["livekit_url"] == settings.livekit_url
        assert data["room_name"] == str(room["id"])

        claims = pyjwt.decode(data["livekit_token"], settings.livekit_api_secret, algorithms=["HS256"])
        assert claims["iss"] == settings.livekit_api_key
        assert claims["sub"] == str(alice["id"])
        assert claims["name"] == "Alice Tester"
        video = claims["video"]
        assert video["room"] == str(room["id"])
        assert video["roomJoin"] is True
        assert video["canPublish"] is True
        assert video["canSubscribe"] is True
        assert video["canPublishData"] is True

    def test_token_unknown_room_returns_404(self, client: TestClient, alice: dict):
        assert client.post("/api/v1/rooms/999999/token").status_code == 404


class TestParticipants:
    def test_participants_reflect_redis_set(self, client: TestClient, alice: dict):
        room = create_room(client, f"part-room-{alice['id']}")
        key = f"room:{room['id']}:participants"

        empty = client.get(f"/api/v1/rooms/{room['id']}/participants").json()
        assert empty == {"room_id": room["id"], "count": 0, "participants": []}

        try:
            sadd(key, "11", "22")
            joined = client.get(f"/api/v1/rooms/{room['id']}/participants").json()
            assert joined["count"] == 2
            assert set(joined["participants"]) == {"11", "22"}
        finally:
            redis_delete(key)

    def test_participants_unknown_room_returns_404(self, client: TestClient, alice: dict):
        assert client.get("/api/v1/rooms/999999/participants").status_code == 404


class TestLivekitWebhook:
    def _post_webhook(self, client: TestClient, token: str, payload: dict):
        return client.post(
            "/api/v1/rooms/livekit/webhook",
            headers={"Authorization": token},
            json=payload,
        )

    def test_join_then_left_updates_participants_and_ends_room(self, client: TestClient, alice: dict):
        from app.integration.livekit import create_token

        room = create_room(client, f"hook-room-{alice['id']}")
        room_id = str(room["id"])
        key = f"room:{room_id}:participants"
        webhook_token = create_token("webhook-internal", "livekit-server")

        try:
            joined = self._post_webhook(
                client,
                webhook_token,
                {"event": "participant_joined", "room": {"name": room_id}, "participant": {"identity": "77"}},
            )
            assert joined.status_code == 200
            assert "77" in smembers(key)

            self._post_webhook(
                client,
                webhook_token,
                {"event": "participant_joined", "room": {"name": room_id}, "participant": {"identity": "88"}},
            )

            left_first = self._post_webhook(
                client,
                webhook_token,
                {"event": "participant_left", "room": {"name": room_id}, "participant": {"identity": "77"}},
            )
            assert left_first.status_code == 200
            assert "88" in smembers(key)

            self._post_webhook(
                client,
                webhook_token,
                {"event": "participant_left", "room": {"name": room_id}, "participant": {"identity": "88"}},
            )

            assert smembers(key) == set()
            status = client.get(f"/api/v1/rooms/{room['id']}").json()["status"]
            assert status == "ended"
        finally:
            redis_delete(key)

    def test_ai_identity_is_ignored(self, client: TestClient, alice: dict):
        from app.integration.livekit import create_token

        room = create_room(client, f"ai-room-{alice['id']}")
        room_id = str(room["id"])
        key = f"room:{room_id}:participants"
        webhook_token = create_token("webhook-internal", "livekit-server")

        try:
            for identity in ("ai_assistant", "ai_observer"):
                self._post_webhook(
                    client,
                    webhook_token,
                    {"event": "participant_joined", "room": {"name": room_id}, "participant": {"identity": identity}},
                )
            assert smembers(key) == set()
        finally:
            redis_delete(key)

    def test_invalid_webhook_token_returns_401(self, client: TestClient, alice: dict):
        response = self._post_webhook(
            client,
            "not-a-valid-token",
            {"event": "participant_joined", "room": {"name": "1"}, "participant": {"identity": "9"}},
        )
        assert response.status_code == 401

    def test_event_without_room_name_is_ignored(self, client: TestClient, alice: dict):
        from app.integration.livekit import create_token

        webhook_token = create_token("webhook-internal", "livekit-server")
        response = self._post_webhook(client, webhook_token, {"event": "participant_joined"})
        assert response.status_code == 200
        assert response.json()["status"] == "ignored"
