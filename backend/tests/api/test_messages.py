from __future__ import annotations

import json

from fastapi.testclient import TestClient

from tests.conftest import make_user, switch_to


def create_message(client: TestClient, room_id: int, text: str, **extra) -> dict:
    payload = {"room_id": room_id, "text": text, "role": "user", **extra}
    response = client.post("/api/v1/messages/", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


class TestCreateMessage:
    def test_create_forces_user_role(self, client: TestClient, alice: dict):
        room = client.post("/api/v1/rooms/", json={"name": f"msg-room-{alice['id']}"}).json()
        message = create_message(client, room["id"], "hello world", role="ai")
        assert message["role"] == "user"
        assert message["user_id"] == alice["id"]

    def test_create_persists_meta_data(self, client: TestClient, alice: dict):
        room = client.post("/api/v1/rooms/", json={"name": f"meta-room-{alice['id']}"}).json()
        message = create_message(client, room["id"], "spoken line", meta_data='{"source": "speech"}')
        assert json.loads(message["meta_data"]) == {"source": "speech"}


class TestAtAiTrigger:
    def test_at_ai_enqueues_answer_job(self, client: TestClient, alice: dict, ai_mocks):
        room = client.post("/api/v1/rooms/", json={"name": f"aiq-room-{alice['id']}"}).json()
        message = create_message(client, room["id"], "@AI   explain phrasal verbs")

        ai_mocks["message_enqueue"].assert_called_once_with(
            room["id"], "answer", "explain phrasal verbs", message["id"]
        )

    def test_lowercase_at_ai_triggers(self, client: TestClient, alice: dict, ai_mocks):
        room = client.post("/api/v1/rooms/", json={"name": f"low-room-{alice['id']}"}).json()
        create_message(client, room["id"], "@ai help me")
        assert ai_mocks["message_enqueue"].called

    def test_plain_message_does_not_enqueue(self, client: TestClient, alice: dict, ai_mocks):
        room = client.post("/api/v1/rooms/", json={"name": f"plain-room-{alice['id']}"}).json()
        create_message(client, room["id"], "just chatting here")
        ai_mocks["message_enqueue"].assert_not_called()

    def test_bare_at_ai_without_query_does_not_enqueue(self, client: TestClient, alice: dict, ai_mocks):
        room = client.post("/api/v1/rooms/", json={"name": f"bare-room-{alice['id']}"}).json()
        create_message(client, room["id"], "@ai   ")
        ai_mocks["message_enqueue"].assert_not_called()


class TestListMessages:
    def test_filters_by_room_role_and_user(self, client: TestClient, alice: dict):
        room_a = client.post("/api/v1/rooms/", json={"name": f"filt-a-{alice['id']}"}).json()
        room_b = client.post("/api/v1/rooms/", json={"name": f"filt-b-{alice['id']}"}).json()

        mine = create_message(client, room_a["id"], "room a user line")
        create_message(client, room_b["id"], "room b noise")

        in_room = client.get(f"/api/v1/messages/?room_id={room_a['id']}").json()
        assert [m["text"] for m in in_room] == ["room a user line"]

        by_user = client.get(f"/api/v1/messages/?user_id={alice['id']}&room_id={room_a['id']}").json()
        assert by_user[0]["id"] == mine["id"]

    def test_count_filtered_by_room(self, client: TestClient, alice: dict):
        room = client.post("/api/v1/rooms/", json={"name": f"cnt-room-{alice['id']}"}).json()
        create_message(client, room["id"], "one")
        create_message(client, room["id"], "two")
        count = client.get(f"/api/v1/messages/count?room_id={room['id']}").json()["count"]
        assert count == 2

    def test_get_single_message_and_404(self, client: TestClient, alice: dict):
        room = client.post("/api/v1/rooms/", json={"name": f"get-room-{alice['id']}"}).json()
        message = create_message(client, room["id"], "fetch me")
        fetched = client.get(f"/api/v1/messages/{message['id']}")
        assert fetched.status_code == 200
        assert fetched.json()["text"] == "fetch me"
        assert client.get("/api/v1/messages/999999").status_code == 404


class TestDeleteMessage:
    def test_author_can_delete_own_message(self, client: TestClient, alice: dict):
        room = client.post("/api/v1/rooms/", json={"name": f"delm-room-{alice['id']}"}).json()
        message = create_message(client, room["id"], "delete me")
        deleted = client.delete(f"/api/v1/messages/{message['id']}")
        assert deleted.status_code == 200
        assert client.get(f"/api/v1/messages/{message['id']}").status_code == 404

    def test_other_user_delete_returns_403(self, client: TestClient, alice: dict):
        room = client.post("/api/v1/rooms/", json={"name": f"guardm-room-{alice['id']}"}).json()
        message = create_message(client, room["id"], "not yours")

        bob = make_user(client)
        switch_to(client, bob)
        response = client.delete(f"/api/v1/messages/{message['id']}")
        assert response.status_code == 403
        switch_to(client, alice)

    def test_delete_unknown_returns_404(self, client: TestClient, alice: dict):
        assert client.delete("/api/v1/messages/999999").status_code == 404
