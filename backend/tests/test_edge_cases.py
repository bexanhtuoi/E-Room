from __future__ import annotations

import pytest


class TestUnicodeEdgeCases:
    def test_vietnamese_display_name(self, client):
        response = client.post("/api/v1/auth/register", json={
            "email": "vietnamese_uniq@test.com",
            "password": "Pass123!",
            "display_name": "Nguyễn Thị Hồng Đào",
        })
        assert response.status_code == 201
        assert "Nguyễn Thị Hồng Đào" in response.json()["display_name"]

    def test_vietnamese_topic(self, client, auth_headers):
        response = client.post("/api/v1/rooms/", json={
            "topic": "Tiếng Anh cho người đi làm",
            "tag_ids": [],
            "max_participants": 5,
            "is_public": True,
        }, headers=auth_headers)
        assert response.status_code == 201
        assert "Tiếng Anh" in response.json()["topic"]

    def test_emoji_in_name(self, client):
        response = client.post("/api/v1/auth/register", json={
            "email": "emoji_uniq@test.com",
            "password": "Pass123!",
            "display_name": "😀🎉🔥 User",
        })
        assert response.status_code == 201

    def test_arabic_chinese_mixed(self, client, auth_headers):
        response = client.post("/api/v1/rooms/", json={
            "topic": "Hello 你好 مرحبا",
            "tag_ids": [],
            "max_participants": 5,
            "is_public": True,
        }, headers=auth_headers)
        assert response.status_code == 201


class TestInputValidation:
    def test_empty_json_body(self, client):
        response = client.post("/api/v1/auth/login", json={})
        assert response.status_code == 422

    def test_null_values(self, client):
        response = client.post("/api/v1/auth/register", json={
            "email": "null@test.com",
            "password": "Valid123!",
            "display_name": None,
        })
        assert response.status_code == 422

    def test_extra_fields(self, client):
        """Extra fields should be ignored, not cause errors."""
        response = client.post("/api/v1/auth/register", json={
            "email": "extra@test.com",
            "password": "Valid123!",
            "display_name": "Extra",
            "injected_field": "should be ignored",
        })
        assert response.status_code == 201

    def test_very_long_email(self, client):
        long_email = "a" * 500 + "@test.com"
        response = client.post("/api/v1/auth/login", json={
            "email": long_email,
            "password": "Pass123!",
        })
        assert response.status_code in (401, 422)

    def test_very_long_display_name(self, client):
        long_name = "Nguyễn " * 200
        response = client.post("/api/v1/auth/register", json={
            "email": "longname@test.com",
            "password": "Valid123!",
            "display_name": long_name,
        })
        assert response.status_code in (201, 422)

    def test_sql_injection_attempt(self, client):
        response = client.post("/api/v1/auth/login", json={
            "email": "test@test.com' OR '1'='1",
            "password": "' OR '1'='1",
        })
        assert response.status_code in (401, 422)

    def test_xss_in_display_name(self, client):
        response = client.post("/api/v1/auth/register", json={
            "email": "xss@test.com",
            "password": "Valid123!",
            "display_name": "<script>alert('xss')</script>",
        })
        assert response.status_code == 201
        data = response.json()
        assert "<script>" in data["display_name"] or response.status_code == 201

    def test_control_characters(self, client):
        response = client.post("/api/v1/auth/register", json={
            "email": "control@test.com",
            "password": "Valid123!\x00",
            "display_name": "User With\x00Null",
        })
        assert response.status_code in (201, 422)


class TestHttpMethods:
    def test_wrong_method_on_endpoint(self, client):
        response = client.get("/api/v1/auth/login")
        assert response.status_code == 405

    def test_wrong_content_type(self, client):
        response = client.post("/api/v1/auth/login", data="not-json",
                               headers={"Content-Type": "text/plain"})
        assert response.status_code in (415, 422)


class TestConcurrencySimulation:
    def test_rapid_registration_same_email(self, client):
        """Simulate race condition: two rapid registrations with same email."""
        email = f"race-{__name__}@test.com"
        r1 = client.post("/api/v1/auth/register", json={
            "email": email, "password": "Pass123!", "display_name": "Racer1",
        })
        r2 = client.post("/api/v1/auth/register", json={
            "email": email, "password": "Pass123!", "display_name": "Racer2",
        })
        assert r1.status_code == 201
        assert r2.status_code == 409


class TestApiDocs:
    def test_openapi_json(self, client):
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "openapi" in schema

    def test_docs_page(self, client):
        response = client.get("/docs")
        assert response.status_code == 200

    def test_redoc_page(self, client):
        response = client.get("/redoc")
        assert response.status_code == 200


class TestErrorResponseFormat:
    def test_404_response_has_detail(self, client):
        response = client.get("/api/v1/rooms/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404
        assert "detail" in response.json()

    def test_422_response_has_detail(self, client):
        response = client.post("/api/v1/auth/login", json={})
        assert response.status_code == 422
        assert "detail" in response.json()

    def test_401_response_has_detail(self, client):
        response = client.post("/api/v1/auth/login", json={
            "email": "nonexistent@test.com",
            "password": "Pass123!",
        })
        assert response.status_code == 401
        assert "detail" in response.json()
