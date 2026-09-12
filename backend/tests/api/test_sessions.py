from __future__ import annotations

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from tests.conftest import make_user, switch_to


def make_room_with_message(client: TestClient, name: str) -> dict:
    room = client.post("/api/v1/rooms/", json={"name": name}).json()
    client.post(f"/api/v1/rooms/{room['id']}/join")
    client.post("/api/v1/messages/", json={"room_id": room["id"], "text": "hello session world", "role": "user"})
    return room


def make_session_with_lines(texts: list, room_id: int) -> int:
    from sqlmodel import Session as DBSession

    from app.database import engine
    from app.models import MessageRole
    from app.services import message_crud
    from app.services.session import session_crud

    with DBSession(engine) as db:
        db_session = session_crud.create(db, obj_in={"user_id": 1, "room_id": room_id})
        for text in texts:
            message_crud.create(
                db,
                obj_in={"room_id": room_id, "user_id": None, "role": MessageRole.USER, "text": text},
            )
        return db_session.id


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

        with patch("app.api.routers.session.run_query", new=AsyncMock(return_value="They said hello.")) as mock_run:
            response = client.post(f"/api/v1/sessions/{session_id}/chat", json={"question": "What was said?"})

        assert response.status_code == 200, response.text
        assert "hello" in response.json()["answer"]

        assert mock_run.call_args[0] == ("What was said?",)
        assert mock_run.call_args[1].get("agent") is not None

        client.post(f"/api/v1/rooms/{room['id']}/leave")

    def test_agent_tool_reads_older_lines(self):
        from app.ai.tools import get_more_messages

        session_id = make_session_with_lines([f"line {i}" for i in range(60)], room_id=771001)

        out = get_more_messages.invoke({"session_id": session_id, "start_index": 0, "count": 2})
        assert "line 0" in out and "line 1" in out
        assert "line 59" not in out
        assert get_more_messages.invoke({"session_id": session_id, "start_index": 9999}).startswith("No more lines")

    def test_agent_tool_reports_index_range(self):
        from app.ai.tools import transcript_info

        session_id = make_session_with_lines(["hi", "hello"], room_id=771002)

        out = transcript_info.invoke({"session_id": session_id})
        assert "2 lines" in out and "0-1" in out

    def test_agent_tool_searches_transcript(self):
        from app.ai.tools import search_transcript

        session_id = make_session_with_lines(
            ["I love rainy days", "Sunny days are best", "Rainy mood again"],
            room_id=771003,
        )

        out = search_transcript.invoke({"session_id": session_id, "keyword": "rainy"})
        assert "[0]" in out and "[2]" in out and "[1]" not in out
        assert search_transcript.invoke({"session_id": session_id, "keyword": "xyz"}).startswith("No line")
        assert "at least 2" in search_transcript.invoke({"session_id": session_id, "keyword": "x"})

    def test_agent_tool_missing_session(self):
        from app.ai.tools import get_more_messages, search_transcript, transcript_info

        assert transcript_info.invoke({"session_id": 999999999}) == "This session has no transcript lines."
        assert get_more_messages.invoke({"session_id": 999999999}).startswith("No more lines")
        assert search_transcript.invoke({"session_id": 999999999, "keyword": "hi"}).startswith("No line")

    def test_chat_stream_emits_sse_events(self, client: TestClient, alice: dict):
        room = make_room_with_message(client, f"sess-stream-{alice['id']}")
        client.post(f"/api/v1/rooms/{room['id']}/join")
        session_id = [s for s in client.get("/api/v1/sessions/mine").json()["sessions"] if s["room"]["id"] == room["id"]][0]["session"]["id"]

        async def fake_stream(question, agent=None):
            yield {"kind": "thinking", "text": "Reading transcript…"}
            yield {"kind": "token", "text": "They said hello."}

        with patch("app.api.routers.session.stream_events", side_effect=fake_stream):
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

        with patch("app.api.routers.session.run_query", new=AsyncMock(return_value="Saved answer.")):
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
