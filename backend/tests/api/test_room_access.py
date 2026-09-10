from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.ai.room_context import build_room_context
from app.models import DocumentKind
from tests.conftest import make_user, register, switch_to, unique_email
from types import SimpleNamespace


def make_private_room(client: TestClient, alice: dict, name: str, emails=None) -> dict:
    payload = {"name": name, "is_private": True, "allowed_emails": emails or []}
    response = client.post("/api/v1/rooms/", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


class TestPrivateRooms:
    def test_host_sees_own_private_room(self, client: TestClient, alice: dict):
        room = make_private_room(client, alice, f"priv-{alice['id']}")

        assert room["is_private"] is True
        assert client.get(f"/api/v1/rooms/{room['id']}").status_code == 200

    def test_stranger_cannot_read_join_or_token(self, client: TestClient, alice: dict):
        room = make_private_room(client, alice, f"priv2-{alice['id']}")
        bob = make_user(client)
        switch_to(client, bob)

        assert client.get(f"/api/v1/rooms/{room['id']}").status_code == 403
        assert client.post(f"/api/v1/rooms/{room['id']}/join").status_code == 403
        assert client.post(f"/api/v1/rooms/{room['id']}/token").status_code == 403

        switch_to(client, alice)

    def test_allowed_email_can_enter(self, client: TestClient, alice: dict):
        friend_email = unique_email()
        room = make_private_room(client, alice, f"priv3-{alice['id']}", [friend_email])
        assert friend_email in room["allowed_emails"]

        friend = register(client, friend_email, "Friend")
        switch_to(client, friend)

        assert client.get(f"/api/v1/rooms/{room['id']}").status_code == 200
        assert client.post(f"/api/v1/rooms/{room['id']}/join").status_code == 200

        switch_to(client, alice)

    def test_private_hidden_from_public_list(self, client: TestClient, alice: dict):
        room = make_private_room(client, alice, f"priv4-{alice['id']}")
        bob = make_user(client)
        switch_to(client, bob)

        public_ids = [r["id"] for r in client.get("/api/v1/rooms/?public_only=true").json()]
        assert room["id"] not in public_ids

        all_ids = [r["id"] for r in client.get("/api/v1/rooms/").json()]
        assert room["id"] not in all_ids

        switch_to(client, alice)
        mine_ids = [r["id"] for r in client.get("/api/v1/rooms/").json()]
        assert room["id"] in mine_ids


class TestRoomSkills:
    def test_host_crud_skills(self, client: TestClient, alice: dict):
        room = client.post("/api/v1/rooms/", json={"name": f"skill-{alice['id']}"}).json()

        created = client.post(
            f"/api/v1/rooms/{room['id']}/skills",
            json={"name": "Vocab coach", "prompt": "Explain new words simply."},
        )
        assert created.status_code == 201
        assert created.json()["kind"] == "skill"
        assert created.json()["content"] == "Explain new words simply."

        listed = client.get(f"/api/v1/rooms/{room['id']}/skills").json()
        assert len(listed) == 1

        updated = client.patch(
            f"/api/v1/rooms/{room['id']}/skills/{created.json()['id']}",
            json={"enabled": False},
        )
        assert updated.json()["enabled"] is False

        deleted = client.delete(f"/api/v1/rooms/{room['id']}/skills/{created.json()['id']}")
        assert deleted.status_code == 200
        assert client.get(f"/api/v1/rooms/{room['id']}/skills").json() == []

    def test_stranger_cannot_touch_skills(self, client: TestClient, alice: dict):
        room = client.post("/api/v1/rooms/", json={"name": f"skill2-{alice['id']}"}).json()
        bob = make_user(client)
        switch_to(client, bob)

        assert client.get(f"/api/v1/rooms/{room['id']}/skills").status_code == 403
        assert client.post(f"/api/v1/rooms/{room['id']}/skills", json={"name": "X", "prompt": "Y"}).status_code == 403

        switch_to(client, alice)


class TestRoomDocuments:
    def test_upload_lists_and_deletes(self, client: TestClient, alice: dict):
        room = client.post("/api/v1/rooms/", json={"name": f"doc-{alice['id']}"}).json()

        with (
            patch("app.integration.minio.put_document", return_value="documents/abc_notes.md"),
            patch("app.integration.minio.get_object", return_value=b"# hello\nsome english notes"),
            patch("app.ai.vector_store.process_document", return_value=None),
            patch("app.integration.minio.delete_object", return_value=None),
            patch("app.ai.vector_store.delete_document_vectors", return_value=0),
        ):
            uploaded = client.post(
                f"/api/v1/rooms/{room['id']}/documents",
                files={"file": ("notes.md", b"# hello\nsome english notes", "text/markdown")},
            )
            assert uploaded.status_code == 201, uploaded.text
            assert uploaded.json()["room_id"] == room["id"]

            listed = client.get(f"/api/v1/rooms/{room['id']}/documents").json()
            assert len(listed) == 1

            doc_id = uploaded.json()["id"]
            downloaded = client.get(f"/api/v1/rooms/{room['id']}/documents/{doc_id}/file")
            assert downloaded.status_code == 200
            assert b"hello" in downloaded.content

            deleted = client.delete(f"/api/v1/rooms/{room['id']}/documents/{doc_id}")
            assert deleted.status_code == 200

    def test_rejects_bad_files(self, client: TestClient, alice: dict):
        room = client.post("/api/v1/rooms/", json={"name": f"doc2-{alice['id']}"}).json()

        bad = client.post(
            f"/api/v1/rooms/{room['id']}/documents",
            files={"file": ("evil.exe", b"MZ", "application/octet-stream")},
        )
        assert bad.status_code == 400


class TestRoomContext:
    def test_empty_room_gives_empty_context(self):
        room = SimpleNamespace(id=1, name="Plain", system_prompt=None)
        assert build_room_context(room, []) == ""

    def test_context_holds_prompt_skills_and_tag(self):
        room = SimpleNamespace(id=7, name="Cinema", system_prompt="Speak slowly.")
        skills = [
            SimpleNamespace(kind=DocumentKind.SKILL, file_name="Coach", content="Correct gently.", enabled=True),
            SimpleNamespace(kind=DocumentKind.SKILL, file_name="Off", content="Ignore me.", enabled=False),
            SimpleNamespace(kind=DocumentKind.FILE, file_name="notes.md", content=None, enabled=True),
        ]

        context = build_room_context(room, skills)

        assert "Speak slowly." in context
        assert "Coach" in context and "Correct gently." in context
        assert "Ignore me." not in context
        assert "tag='room:7'" in context
