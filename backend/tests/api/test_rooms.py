from __future__ import annotations

import jwt as pyjwt
from fastapi.testclient import TestClient

from app.config import settings
from app.integration.redis import delete as redis_delete
from app.integration.redis import sadd, smembers
from tests.conftest import make_user, switch_to


def create_room(client: TestClient, name: str) -> dict:
    response = client.post("/api/v1/rooms/", json={"name": name, "max_participants": 4})
    assert response.status_code == 201, response.text
    return response.json()


class TestRoomCrud:
    def test_create_room_sets_host(self, client: TestClient, alice: dict):
        room = create_room(client, f"room-{alice['id']}-host")
        assert room["host_id"] == alice["id"]
        assert room["status"] == "idle"
        assert room["max_participants"] == 4

    def test_create_duplicate_name_returns_400(self, client: TestClient, alice: dict):
        name = f"dup-room-{alice['id']}"
        create_room(client, name)
        duplicate = client.post("/api/v1/rooms/", json={"name": name})
        assert duplicate.status_code == 400

    def test_list_and_count_rooms(self, client: TestClient, alice: dict):
        create_room(client, f"list-room-{alice['id']}")
        listed = client.get("/api/v1/rooms/?limit=100").json()
        names = [r["name"] for r in listed]
        assert f"list-room-{alice['id']}" in names
        assert client.get("/api/v1/rooms/count").json()["count"] >= 1

    def test_list_rooms_newest_first(self, client: TestClient, alice: dict):
        first = create_room(client, f"order-a-{alice['id']}")
        second = create_room(client, f"order-b-{alice['id']}")
        listed = client.get("/api/v1/rooms/?limit=100").json()
        ids = [r["id"] for r in listed]
        assert ids.index(second["id"]) < ids.index(first["id"])

    def test_list_rooms_pagination_window(self, client: TestClient, alice: dict):
        page_one = client.get("/api/v1/rooms/?limit=2").json()
        assert len(page_one) <= 2
        page_two = client.get("/api/v1/rooms/?limit=2&skip=2").json()
        ids_one = {r["id"] for r in page_one}
        ids_two = {r["id"] for r in page_two}
        assert ids_one.isdisjoint(ids_two)

    def test_get_room_by_id_and_404(self, client: TestClient, alice: dict):
        room = create_room(client, f"get-room-{alice['id']}")
        fetched = client.get(f"/api/v1/rooms/{room['id']}").json()
        assert fetched["name"] == room["name"]
        assert client.get("/api/v1/rooms/999999").status_code == 404

    def test_update_by_host(self, client: TestClient, alice: dict):
        room = create_room(client, f"upd-room-{alice['id']}")
        updated = client.patch(f"/api/v1/rooms/{room['id']}", json={"name": "New Topic Room", "status": "active"})
        assert updated.status_code == 200
        assert updated.json()["name"] == "New Topic Room"
        assert updated.json()["status"] == "active"

    def test_update_by_non_host_returns_403(self, client: TestClient, alice: dict):
        room = create_room(client, f"guard-room-{alice['id']}")
        bob = make_user(client)
        switch_to(client, bob)
        response = client.patch(f"/api/v1/rooms/{room['id']}", json={"name": "Hijack"})
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

    def test_leave_endpoint_removes_self_and_idles_empty_room(self, client: TestClient, alice: dict):
        from app.integration.redis import smembers as redis_smembers

        room = create_room(client, f"leave-room-{alice['id']}")
        key = f"room:{room['id']}:participants"

        try:
            sadd(key, str(alice["id"]))
            assert str(alice["id"]) in redis_smembers(key)

            response = client.post(f"/api/v1/rooms/{room['id']}/leave")
            assert response.status_code == 200
            assert response.json() == {"status": "left", "room_id": room["id"]}
            assert redis_smembers(key) == set()
        finally:
            redis_delete(key)


class TestLivekitWebhook:
    def _post_webhook(self, client: TestClient, token: str, payload: dict):
        return client.post(
            "/api/v1/rooms/livekit/webhook",
            headers={"Authorization": token},
            json=payload,
        )

    def test_join_then_left_updates_participants_and_idles_room(self, client: TestClient, alice: dict):
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
            # Phong het nguoi → IDLE (van hien trong list), khong ENDED ngay
            status = client.get(f"/api/v1/rooms/{room['id']}").json()["status"]
            assert status == "idle"
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


class TestRoomMatch:
    def test_match_returns_open_room(self, client: TestClient, alice: dict):
        response = client.post("/api/v1/rooms/match", json={})
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["status"] == "matched"
        assert body["room"]["status"] in ("active", "idle")

    def test_match_prefers_active_over_idle(self, client: TestClient, alice: dict):
        idle = create_room(client, f"idle-match-{alice['id']}")
        assert client.patch(f"/api/v1/rooms/{idle['id']}", json={"status": "idle"}).status_code == 200
        active = create_room(client, f"active-match-{alice['id']}")
        assert client.patch(f"/api/v1/rooms/{active['id']}", json={"status": "active"}).status_code == 200
        response = client.post("/api/v1/rooms/match", json={})
        assert response.status_code == 200
        assert response.json()["room"]["status"] == "active"

    def test_match_filters_by_topic(self, client: TestClient, alice: dict):
        cinema = create_room(client, f"cinema-match-{alice['id']}")
        assert client.patch(f"/api/v1/rooms/{cinema['id']}", json={"topics": ["Cinema"]}).status_code == 200
        response = client.post("/api/v1/rooms/match", json={"topic": "cinema"})
        assert response.status_code == 200
        room = response.json()["room"]
        topics = room.get("topics") or []
        topics_text = " ".join(topics) if isinstance(topics, list) else str(topics)
        haystack = " ".join([room.get("name") or "", room.get("description") or "", topics_text]).lower()
        assert "cinema" in haystack

    def test_match_requires_auth(self):
        from app.main import app
        from fastapi.testclient import TestClient as RawClient

        raw = RawClient(app)
        assert raw.post("/api/v1/rooms/match", json={}).status_code == 403


class TestRoomTopics:
    def test_create_room_normalizes_topics(self, client: TestClient, alice: dict):
        response = client.post(
            "/api/v1/rooms/",
            json={
                "name": f"topic-room-{alice['id']}",
                "topics": ["ai agents", "AI Agents", "  art  ", ""],
                "description": "  A place to talk.  ",
            },
        )
        assert response.status_code == 201, response.text
        room = response.json()
        assert room["topics"] == ["Ai Agents", "Art"]
        assert room["description"] == "A place to talk."

    def test_create_room_rejects_more_than_five_topics(self, client: TestClient, alice: dict):
        response = client.post(
            "/api/v1/rooms/",
            json={"name": f"many-topics-{alice['id']}", "topics": ["A", "B", "C", "D", "E", "F"]},
        )
        assert response.status_code == 422

    def test_create_room_rejects_more_than_four_seats(self, client: TestClient, alice: dict):
        response = client.post(
            "/api/v1/rooms/",
            json={"name": f"big-room-{alice['id']}", "max_participants": 8},
        )
        assert response.status_code == 422

    def test_update_room_topics(self, client: TestClient, alice: dict):
        room = create_room(client, f"upd-topics-{alice['id']}")
        updated = client.patch(f"/api/v1/rooms/{room['id']}", json={"topics": ["cinema", "photography"]})
        assert updated.status_code == 200, updated.text
        assert updated.json()["topics"] == ["Cinema", "Photography"]

    def test_update_room_feature_flags(self, client: TestClient, alice: dict):
        room = create_room(client, f"upd-flags-{alice['id']}")
        assert room["enable_heartbeat"] is True
        updated = client.patch(
            f"/api/v1/rooms/{room['id']}",
            json={"enable_heartbeat": False, "enable_transcript": False, "enable_agent": True},
        )
        assert updated.status_code == 200, updated.text
        body = updated.json()
        assert body["enable_heartbeat"] is False
        assert body["enable_transcript"] is False
        assert body["enable_agent"] is True
