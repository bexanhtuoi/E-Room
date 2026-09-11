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

    def test_agent_tool_reports_index_range(self):
        from app.ai.session_agent import build_transcript_info_tool

        lines = [{"speaker": "Ann", "text": "hi"}, {"speaker": "Bob", "text": "hello"}]
        transcript_info = build_transcript_info_tool(lines)

        assert transcript_info.name == "transcript_info"
        out = transcript_info.invoke({})
        assert "2 lines" in out and "0-1" in out
        assert "Ann" in out and "Bob" in out

    def test_agent_tool_searches_transcript(self):
        from app.ai.session_agent import build_search_transcript_tool

        lines = [
            {"speaker": "Ann", "text": "I love rainy days"},
            {"speaker": "Bob", "text": "Sunny days are best"},
            {"speaker": "Ann", "text": "Rainy mood again"},
        ]
        search_transcript = build_search_transcript_tool(lines)

        assert search_transcript.name == "search_transcript"
        out = search_transcript.invoke({"keyword": "rainy"})
        assert "[0]" in out and "[2]" in out and "[1]" not in out
        assert search_transcript.invoke({"keyword": "xyz"}).startswith("No line")
        assert "at least 2" in search_transcript.invoke({"keyword": "x"})

    def test_chat_stream_emits_sse_events(self, client: TestClient, alice: dict):
        room = make_room_with_message(client, f"sess-stream-{alice['id']}")
        client.post(f"/api/v1/rooms/{room['id']}/join")
        session_id = [s for s in client.get("/api/v1/sessions/mine").json()["sessions"] if s["room"]["id"] == room["id"]][0]["session"]["id"]

        async def fake_stream(question, all_lines):
            yield {"kind": "thinking", "text": "Reading transcript…"}
            yield {"kind": "token", "text": "They said hello."}

        with patch("app.ai.session_agent.stream_session_agent", side_effect=fake_stream):
            with client.stream("POST", f"/api/v1/sessions/{session_id}/chat/stream", json={"question": "What was said?"}) as response:
                assert response.status_code == 200, response.text
                body = response.read().decode()

        assert "Reading transcript" in body
        assert "They said hello." in body
        assert '"kind": "done"' in body

        client.post(f"/api/v1/rooms/{room['id']}/leave")

    def test_chat_stream_empty_session_errors(self, client: TestClient, alice: dict):
        room = client.post("/api/v1/rooms/", json={"name": f"sess-nostream-{alice['id']}"}).json()
        client.post(f"/api/v1/rooms/{room['id']}/join")
        session_id = [s for s in client.get("/api/v1/sessions/mine").json()["sessions"] if s["room"]["id"] == room["id"]][0]["session"]["id"]

        with client.stream("POST", f"/api/v1/sessions/{session_id}/chat/stream", json={"question": "Hi?"}) as response:
            assert response.status_code == 200
            body = response.read().decode()

        assert '"kind": "error"' in body and "No messages" in body

        client.post(f"/api/v1/rooms/{room['id']}/leave")

    def test_chat_persists_turns_with_session_meta(self, client: TestClient, alice: dict):
        room = make_room_with_message(client, f"sess-save-{alice['id']}")
        client.post(f"/api/v1/rooms/{room['id']}/join")
        session_id = [s for s in client.get("/api/v1/sessions/mine").json()["sessions"] if s["room"]["id"] == room["id"]][0]["session"]["id"]

        with patch("app.ai.session_agent.run_session_agent", new=AsyncMock(return_value="Saved answer.")):
            assert client.post(f"/api/v1/sessions/{session_id}/chat", json={"question": "Remember me?"}).status_code == 200

        data = client.get(f"/api/v1/sessions/{session_id}/messages").json()
        assert data["chat"] == [
            {"role": "user", "text": "Remember me?"},
            {"role": "ai", "text": "Saved answer."},
        ]
        # Transcript van sach — Q&A khong tron vao context session
        assert "Remember me?" not in data["transcript"]

        # Room chat khong thay tin Q&A
        room_texts = [m["text"] for m in client.get("/api/v1/messages/", params={"room_id": room["id"]}).json()]
        assert "Remember me?" not in room_texts and "Saved answer." not in room_texts

        client.post(f"/api/v1/rooms/{room['id']}/leave")

    def test_empty_question_rejected(self, client: TestClient, alice: dict):
        room = make_room_with_message(client, f"sess-empty-{alice['id']}")
        client.post(f"/api/v1/rooms/{room['id']}/join")
        session_id = [s for s in client.get("/api/v1/sessions/mine").json()["sessions"] if s["room"]["id"] == room["id"]][0]["session"]["id"]

        assert client.post(f"/api/v1/sessions/{session_id}/chat", json={"question": "  "}).status_code == 400

        client.post(f"/api/v1/rooms/{room['id']}/leave")
