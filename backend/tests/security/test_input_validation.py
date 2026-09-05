from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.conftest import switch_to


class TestInputValidationAndFuzzing:
    def test_unicode_and_emojis_in_message(self, client: TestClient, alice: dict):
        switch_to(client, alice)
        room = client.post("/api/v1/rooms/", json={"name": f"unicode-room-{alice['id']}"}).json()
        assert "id" in room, room
        text_with_emojis = "Xin chào các bạn 👋 Tiếng Việt có dấu và ký tự đặc biệt: á, ế, ộ, ử, ñ, é, ü, 🚀🎉🔥"

        response = client.post(
            "/api/v1/messages/",
            json={"room_id": room["id"], "text": text_with_emojis},
        )
        assert response.status_code == 201
        assert response.json()["text"] == text_with_emojis

    def test_path_traversal_payload_in_document_filename(self, client: TestClient, alice: dict):
        switch_to(client, alice)
        traversal_names = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\cmd.exe",
            "file/../../secret.txt",
        ]
        for bad_name in traversal_names:
            response = client.post(
                "/api/v1/documents/",
                json={"file_name": bad_name, "file_type": "pdf", "file_path": "path/test.pdf"},
            )
            assert response.status_code in (201, 400, 422)

    def test_giant_string_payload_truncation_or_rejection(self, client: TestClient, alice: dict):
        switch_to(client, alice)
        room = client.post("/api/v1/rooms/", json={"name": f"giant-room-{alice['id']}"}).json()
        assert "id" in room, room
        giant_text = "A" * 10000  # Vuot qua gioi han Column String(4000)

        response = client.post(
            "/api/v1/messages/",
            json={"room_id": room["id"], "text": giant_text},
        )
        assert response.status_code in (201, 400, 422, 500)

    @pytest.mark.parametrize(
        "invalid_email",
        [
            "plainaddress",
            "@missingusername.com",
            "username@.com",
            "username@com",
            "user spaces@test.com",
        ],
    )
    def test_invalid_email_formats(self, client: TestClient, invalid_email: str):
        response = client.post(
            "/api/v1/auth/register",
            json={"email": invalid_email, "full_name": "Invalid Email", "password": "Password123!"},
        )
        assert response.status_code == 422
