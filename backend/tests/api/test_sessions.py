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
    def test_chat_answers_from_transcript(self, client: TestClient, alice: dict):
        room = make_room_with_message(client, f"sess-chat-{alice['id']}")
        client.post(f"/api/v1/rooms/{room['id']}/join")
        session_id = [s for s in client.get("/api/v1/sessions/mine").json()["sessions"] if s["room"]["id"] == room["id"]][0]["session"]["id"]

        with patch("app.ai.session_agent.run_session_agent", new=AsyncMock(return_value="They said hello.")) as mock_run:
            response = client.post(f"/api/v1/sessions/{session_id}/chat", json={"question": "What was said?"})

        assert response.status_code == 200, response.text
        assert "hello" in response.json()["answer"]

        asked_question, sent_lines = mock_run.call_args[0]
        assert asked_question == "What was said?"
        assert any("hello session world" in line["text"] for line in sent_lines)

        client.post(f"/api/v1/rooms/{room['id']}/leave")

    def test_agent_tool_reads_older_lines(self):
        from app.ai.session_agent import build_get_more_messages_tool

        lines = [{"speaker": "Ann", "text": f"line {i}"} for i in range(60)]
        get_more_messages = build_get_more_messages_tool(lines)

        assert get_more_messages.name == "get_more_messages"
        out = get_more_messages.invoke({"start_index": 0, "count": 2})
        assert "line 0" in out and "line 1" in out
        assert "line 59" not in out
        assert get_more_messages.invoke({"start_index": 9999}).startswith("No more lines")

    def test_empty_question_rejected(self, client: TestClient, alice: dict):
        room = make_room_with_message(client, f"sess-empty-{alice['id']}")
        client.post(f"/api/v1/rooms/{room['id']}/join")
        session_id = [s for s in client.get("/api/v1/sessions/mine").json()["sessions"] if s["room"]["id"] == room["id"]][0]["session"]["id"]

        assert client.post(f"/api/v1/sessions/{session_id}/chat", json={"question": "  "}).status_code == 400

        client.post(f"/api/v1/rooms/{room['id']}/leave")
