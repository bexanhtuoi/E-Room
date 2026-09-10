from __future__ import annotations

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from tests.conftest import make_user, switch_to


def make_room_with_message(client: TestClient, name: str) -> dict:
    room = client.post("/api/v1/rooms/", json={"name": name}).json()
    client.post(f"/api/v1/rooms/{room['id']}/join")
    client.post("/api/v1/messages/", json={"room_id": room["id"], "text": "hello session world", "role": "user"})
    return room


class TestSessionTracking:
    def test_join_opens_and_leave_closes_session(self, client: TestClient, alice: dict):
        room = make_room_with_message(client, f"sess-room-{alice['id']}")

        assert client.post(f"/api/v1/rooms/{room['id']}/join").status_code == 200
        mine = client.get("/api/v1/sessions/mine").json()["sessions"]
        mine = [s for s in mine if s["room"]["id"] == room["id"]]

        assert len(mine) == 1
        assert mine[0]["session"]["left_at"] is None
        assert mine[0]["message_count"] >= 1

        assert client.post(f"/api/v1/rooms/{room['id']}/leave").status_code == 200
        closed = client.get(f"/api/v1/sessions/mine").json()["sessions"]
        closed = [s for s in closed if s["room"]["id"] == room["id"]]

        assert closed[0]["session"]["left_at"] is not None
        assert closed[0]["session"]["duration_seconds"] is not None

    def test_double_join_keeps_single_open_session(self, client: TestClient, alice: dict):
        room = make_room_with_message(client, f"sess-dup-{alice['id']}")

        client.post(f"/api/v1/rooms/{room['id']}/join")
        client.post(f"/api/v1/rooms/{room['id']}/join")
        mine = [s for s in client.get("/api/v1/sessions/mine").json()["sessions"] if s["room"]["id"] == room["id"]]

        assert len(mine) == 1
        client.post(f"/api/v1/rooms/{room['id']}/leave")

    def test_stranger_cannot_read_session(self, client: TestClient, alice: dict):
        room = make_room_with_message(client, f"sess-priv-{alice['id']}")
        client.post(f"/api/v1/rooms/{room['id']}/join")
        session_id = [s for s in client.get("/api/v1/sessions/mine").json()["sessions"] if s["room"]["id"] == room["id"]][0]["session"]["id"]

        bob = make_user(client)
        switch_to(client, bob)
        assert client.get(f"/api/v1/sessions/{session_id}").status_code == 403

        switch_to(client, alice)
        client.post(f"/api/v1/rooms/{room['id']}/leave")


class TestSessionAI:
    def test_summarize_returns_without_saving(self, client: TestClient, alice: dict):
        room = make_room_with_message(client, f"sess-sum-{alice['id']}")
        client.post(f"/api/v1/rooms/{room['id']}/join")
        session_id = [s for s in client.get("/api/v1/sessions/mine").json()["sessions"] if s["room"]["id"] == room["id"]][0]["session"]["id"]

        fake_llm = AsyncMock()
        fake_llm.ainvoke.return_value = type("Msg", (), {"content": "## Summary\nGreat chat."})()

        with patch("app.api.routers.session.get_llm", return_value=fake_llm):
            response = client.post(f"/api/v1/sessions/{session_id}/summarize")

        assert response.status_code == 200, response.text
        assert "Great chat" in response.json()["summary"]

        detail = client.get(f"/api/v1/sessions/{session_id}").json()
        assert "summary" not in detail["session"]

        client.post(f"/api/v1/rooms/{room['id']}/leave")

    def test_ask_uses_transcript(self, client: TestClient, alice: dict):
        room = make_room_with_message(client, f"sess-ask-{alice['id']}")
        client.post(f"/api/v1/rooms/{room['id']}/join")
        session_id = [s for s in client.get("/api/v1/sessions/mine").json()["sessions"] if s["room"]["id"] == room["id"]][0]["session"]["id"]

        fake_llm = AsyncMock()
        fake_llm.ainvoke.return_value = type("Msg", (), {"content": "They said hello."})()

        with patch("app.api.routers.session.get_llm", return_value=fake_llm):
            response = client.post(f"/api/v1/sessions/{session_id}/ask", json={"question": "What was said?"})

        assert response.status_code == 200, response.text
        assert "hello" in response.json()["answer"]

        sent = fake_llm.ainvoke.call_args[0][0]
        assert "SESSION.md" in sent[0].content
        assert "Q&A mode" in sent[1].content
        assert "hello session world" in sent[1].content

        client.post(f"/api/v1/rooms/{room['id']}/leave")

    def test_empty_question_rejected(self, client: TestClient, alice: dict):
        room = make_room_with_message(client, f"sess-empty-{alice['id']}")
        client.post(f"/api/v1/rooms/{room['id']}/join")
        session_id = [s for s in client.get("/api/v1/sessions/mine").json()["sessions"] if s["room"]["id"] == room["id"]][0]["session"]["id"]

        assert client.post(f"/api/v1/sessions/{session_id}/ask", json={"question": "  "}).status_code == 400

        client.post(f"/api/v1/rooms/{room['id']}/leave")
