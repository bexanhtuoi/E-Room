from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.ai.prompt import get_main_prompt, room_system_prompt, room_tag_rule
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


class TestRoomInvites:
    def test_invited_user_gets_notification_once(self, client: TestClient, alice: dict):
        friend_email = unique_email()
        friend = register(client, friend_email, "Invited Friend")
        switch_to(client, alice)

        room = client.post(
            "/api/v1/rooms/",
            json={"name": f"invite-{alice['id']}", "is_private": True, "allowed_emails": [friend_email]},
        ).json()

        switch_to(client, friend)
        notifs = client.get("/api/v1/notifications/").json()
        invites = [n for n in notifs if n["notification_type"] == "invite"]
        assert len(invites) == 1
        assert f"room:{room['id']}" in invites[0]["body"]

        # Patch lai cung danh sach → khong spam them
        switch_to(client, alice)
        client.patch(f"/api/v1/rooms/{room['id']}", json={"allowed_emails": [friend_email]})
        switch_to(client, friend)
        again = [n for n in client.get("/api/v1/notifications/").json() if n["notification_type"] == "invite"]
        assert len(again) == 1

    def test_unknown_email_skipped_silently(self, client: TestClient, alice: dict):
        response = client.post(
            "/api/v1/rooms/",
            json={"name": f"invite-ghost-{alice['id']}", "allowed_emails": ["ghost-nobody@example.com"]},
        )
        assert response.status_code == 201


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
    def test_missing_room_falls_back_to_main_prompt(self):
        assert room_system_prompt(None) == get_main_prompt()

    def test_host_prompt_replaces_main_prompt(self):
        room = SimpleNamespace(id=7, name="Cinema", system_prompt="Speak slowly.")
        assert room_system_prompt(room) == "Speak slowly."

    def test_tag_rule_needs_docs(self):
        room = SimpleNamespace(id=7, name="Cinema", system_prompt=None)
        assert room_tag_rule(room, []) == ""
        documents = [
            SimpleNamespace(kind=DocumentKind.FILE, file_name="notes.md", content=None, enabled=True),
        ]
        assert "retrieval_documents" in room_tag_rule(room, documents)
        assert "only searches this room" in room_tag_rule(room, documents)
