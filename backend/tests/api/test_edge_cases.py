from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.mark.parametrize(
    "query",
    ["?skip=-1", "?limit=0", "?limit=101"],
)
class TestPaginationValidation:
    def test_invalid_pagination_returns_422(self, client: TestClient, query: str):
        assert client.get(f"/api/v1/users/{query}").status_code == 422
        assert client.get(f"/api/v1/rooms/{query}").status_code == 422
        assert client.get(f"/api/v1/messages/{query}").status_code == 422
        assert client.get(f"/api/v1/notifications/{query}").status_code == 422
        assert client.get(f"/api/v1/documents/{query}").status_code == 422


class TestUnauthorizedAccess:
    def test_protected_endpoints_require_auth(self, alice: dict):
        from app.main import app

        raw = TestClient(app)

        assert raw.get("/api/v1/users/me").status_code == 403
        assert raw.post("/api/v1/rooms/", json={"name": "anon-room"}).status_code == 403
        assert raw.post("/api/v1/messages/", json={"room_id": 1, "text": "x"}).status_code == 403
        assert raw.post("/api/v1/documents/", json={"file_name": "a", "file_type": "pdf", "file_path": "p"}).status_code == 403
        assert raw.get("/api/v1/notifications/").status_code == 403
        assert raw.get("/api/v1/rooms/1/participants").status_code == 403
        assert raw.post("/api/v1/rooms/1/token").status_code == 403


class TestUnknownResources:
    def test_unknown_room_returns_404(self, client: TestClient, alice: dict):
        assert client.get("/api/v1/rooms/999999").status_code == 404
        assert client.patch("/api/v1/rooms/999999", json={"topic": "x"}).status_code == 404

    def test_unknown_user_returns_404(self, client: TestClient, alice: dict):
        assert client.get("/api/v1/users/999999").status_code == 404

    def test_unknown_message_and_document_return_404(self, client: TestClient, alice: dict):
        assert client.get("/api/v1/messages/999999").status_code == 404
        assert client.get("/api/v1/documents/999999").status_code == 404


class TestSchemaValidation:
    def test_register_missing_fields_returns_422(self, client: TestClient):
        response = client.post("/api/v1/auth/register", json={"email": "half@test.com"})
        assert response.status_code == 422

    def test_create_message_missing_text_returns_422(self, client: TestClient, alice: dict):
        response = client.post("/api/v1/messages/", json={"room_id": 1})
        assert response.status_code == 422

    def test_notification_patch_requires_is_read(self, client: TestClient, alice: dict):
        created = client.post("/api/v1/notifications/", json={"title": "t"}).json()
        response = client.patch(f"/api/v1/notifications/{created['id']}", json={})
        assert response.status_code == 422
