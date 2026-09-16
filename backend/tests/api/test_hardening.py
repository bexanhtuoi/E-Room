from __future__ import annotations

import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient
from redis.exceptions import RedisError
from sqlmodel import Session

from app.database import engine
from app.main import app
from app.models import RoleEnum, User
from tests.conftest import PASSWORD, make_user, switch_to


def make_client(tag: str) -> TestClient:
    client = TestClient(app)
    email = f"harden_{tag}_{uuid.uuid4().hex[:6]}@test.com"
    response = client.post(
        "/api/v1/auth/register",
        json={"full_name": f"Hardening {tag}", "email": email, "password": PASSWORD},
    )
    assert response.status_code == 201, response.text
    response = client.post("/api/v1/auth/login", data={"username": email, "password": PASSWORD})
    assert response.status_code == 200, response.text
    token = response.cookies.get("access_token")
    if token:
        client.cookies.set("access_token", token)
    return client


def join_quiet(client: TestClient, room_id: int):
    with (
        patch("app.api.routers.room.enqueue_room_observer"),
        patch("app.api.routers.room.enqueue_room_transcriber"),
    ):
        return client.post(f"/api/v1/rooms/{room_id}/join")


def make_admin(client: TestClient) -> dict:
    admin = make_user(client, "Hardening Admin")
    with Session(engine) as db:
        user = db.get(User, int(admin["id"]))
        user.role = RoleEnum.admin
        db.add(user)
        db.commit()
    return admin


class TestRoomCapacity:
    def test_fifth_user_rejected_from_four_seat_room(self):
        from app.integration.redis import delete as redis_delete

        host = make_client("host")
        room = host.post("/api/v1/rooms/", json={"name": f"cap-{uuid.uuid4().hex[:6]}", "max_participants": 4}).json()
        key = f"room:{room['id']}:participants"

        try:
            members = [make_client(f"m{i}") for i in range(4)]
            for member in members:
                assert join_quiet(member, room["id"]).status_code == 200

            outsider = make_client("outsider")
            assert join_quiet(outsider, room["id"]).status_code == 403
            assert outsider.post(f"/api/v1/rooms/{room['id']}/token").status_code == 403

            assert join_quiet(members[0], room["id"]).status_code == 200
            assert members[0].post(f"/api/v1/rooms/{room['id']}/token").status_code == 200

            for member in members:
                member.post(f"/api/v1/rooms/{room['id']}/leave")
        finally:
            redis_delete(key)

    def test_join_stays_open_when_presence_unavailable(self):
        from app.integration.redis import delete as redis_delete

        host = make_client("joinhost")
        room = host.post("/api/v1/rooms/", json={"name": f"capdown-{uuid.uuid4().hex[:6]}"}).json()
        key = f"room:{room['id']}:participants"

        try:
            with patch("app.api.routers.room.scard", side_effect=RedisError("redis down")):
                assert join_quiet(host, room["id"]).status_code == 200
        finally:
            host.post(f"/api/v1/rooms/{room['id']}/leave")
            redis_delete(key)

    def test_participants_unavailable_when_presence_down(self, client: TestClient, alice: dict):
        room = client.post("/api/v1/rooms/", json={"name": f"partdown-{alice['id']}"}).json()

        with patch("app.api.routers.room.smembers", side_effect=RedisError("redis down")):
            assert client.get(f"/api/v1/rooms/{room['id']}/participants").status_code == 503


class TestMessageValidation:
    def test_empty_and_blank_text_rejected(self, client: TestClient, alice: dict):
        room = client.post("/api/v1/rooms/", json={"name": f"val-{alice['id']}"}).json()

        assert client.post("/api/v1/messages/", json={"room_id": room["id"], "text": ""}).status_code == 422
        assert client.post("/api/v1/messages/", json={"room_id": room["id"], "text": "   "}).status_code == 422

    def test_oversize_text_rejected(self, client: TestClient, alice: dict):
        room = client.post("/api/v1/rooms/", json={"name": f"big-{alice['id']}"}).json()

        assert client.post("/api/v1/messages/", json={"room_id": room["id"], "text": "x" * 4001}).status_code == 422
        assert client.post("/api/v1/messages/", json={"room_id": room["id"], "text": "x" * 4000}).status_code == 201


class TestAtAiMentionRules:
    def test_email_like_text_does_not_trigger(self, client: TestClient, alice: dict, ai_mocks):
        room = client.post("/api/v1/rooms/", json={"name": f"mail-{alice['id']}"}).json()
        client.post("/api/v1/messages/", json={"room_id": room["id"], "text": "mail me at foo@ai.com"})

        ai_mocks["message_enqueue"].assert_not_called()

    def test_word_mention_triggers_like_voice_transcript(self, client: TestClient, alice: dict, ai_mocks):
        room = client.post("/api/v1/rooms/", json={"name": f"mid-{alice['id']}"}).json()
        message = client.post("/api/v1/messages/", json={"room_id": room["id"], "text": "hello @ai help me"}).json()

        ai_mocks["message_enqueue"].assert_called_once_with(room["id"], "answer", "help me", message["id"])

    def test_leading_mention_triggers(self, client: TestClient, alice: dict, ai_mocks):
        room = client.post("/api/v1/rooms/", json={"name": f"lead-{alice['id']}"}).json()
        client.post("/api/v1/messages/", json={"room_id": room["id"], "text": "  @AI help me"})

        assert ai_mocks["message_enqueue"].called


class TestDocumentScoping:
    def test_other_user_cannot_read_document(self, client: TestClient, alice: dict):
        created = client.post(
            "/api/v1/documents/",
            json={"file_name": f"priv-{alice['id']}.pdf", "file_type": "pdf", "file_path": "documents/priv.pdf"},
        ).json()

        bob = make_user(client)
        switch_to(client, bob)

        assert client.get(f"/api/v1/documents/{created['id']}").status_code == 403
        listed = client.get("/api/v1/documents/?limit=100").json()
        assert all(d["id"] != created["id"] for d in listed)
        assert client.get("/api/v1/documents/count").json()["count"] == 0

        switch_to(client, alice)
        assert client.get(f"/api/v1/documents/{created['id']}").status_code == 200


class TestMessageScoping:
    def test_unfiltered_list_requires_room_or_self(self, client: TestClient, alice: dict):
        assert client.get("/api/v1/messages/").status_code == 400
        assert client.get(f"/api/v1/messages/?user_id={alice['id']}").status_code == 200
        assert client.get("/api/v1/messages/count").status_code == 400

    def test_other_users_messages_forbidden(self, client: TestClient, alice: dict):
        bob = make_user(client)
        switch_to(client, bob)

        assert client.get(f"/api/v1/messages/?user_id={alice['id']}").status_code == 403

        switch_to(client, alice)

    def test_admin_can_list_everything(self, client: TestClient, alice: dict):
        admin = make_admin(client)
        switch_to(client, admin)

        assert client.get("/api/v1/messages/").status_code == 200
        assert client.get("/api/v1/messages/count").status_code == 200

        switch_to(client, alice)
