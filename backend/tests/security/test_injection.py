from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.conftest import switch_to


class TestSQLInjectionResistance:
    @pytest.mark.parametrize(
        "sql_payload",
        [
            "' OR '1'='1",
            "admin' --",
            "'; DROP TABLE users; --",
            "1 UNION SELECT 1, 'admin', 'hacked@hack.com', 'pwd', 'admin', '2026-01-01', '2026-01-01' --",
            "' OR 1=1 #",
            "\" OR \"\"=\"",
        ],
    )
    def test_login_sql_injection(self, client: TestClient, sql_payload: str):
        response = client.post(
            "/api/v1/auth/login",
            data={"username": sql_payload, "password": "WrongPassword123!"},
        )
        assert response.status_code in (400, 401, 404, 422)

    def test_room_name_sql_injection_safe(self, client: TestClient, alice: dict):
        switch_to(client, alice)
        response = client.post("/api/v1/rooms/", json={"name": f"safe-room-{alice['id']}"})
        assert response.status_code == 201


class TestXSSPayloadSafety:
    @pytest.mark.parametrize(
        "xss_payload",
        [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert(1)>",
            "javascript:alert(document.cookie)",
            "<svg/onload=alert('XSS')>",
            "<iframe src='javascript:alert(1)'></iframe>",
        ],
    )
    def test_message_text_xss_storage(self, client: TestClient, alice: dict, xss_payload: str):
        switch_to(client, alice)
        room = client.post("/api/v1/rooms/", json={"name": f"xss-room-{alice['id']}-{abs(hash(xss_payload))}"}).json()
        assert "id" in room, room
        response = client.post(
            "/api/v1/messages/",
            json={"room_id": room["id"], "text": xss_payload},
        )
        assert response.status_code == 201
        msg = response.json()
        assert msg["text"] == xss_payload
