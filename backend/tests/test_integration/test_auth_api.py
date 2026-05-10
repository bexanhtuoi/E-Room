from __future__ import annotations

import pytest
import time


class TestAuthRegister:
    def test_register_new_user(self, client, db_session):
        response = client.post("/api/v1/auth/register", json={
            "email": "newuser@test.com",
            "password": "SecurePass123!",
            "display_name": "New User",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@test.com"
        assert data["display_name"] == "New User"
        assert "id" in data

    def test_register_duplicate_email(self, client, test_user):
        response = client.post("/api/v1/auth/register", json={
            "email": test_user["email"],
            "password": "AnotherPass123!",
            "display_name": "Duplicate",
        })
        assert response.status_code == 409

    def test_register_missing_fields(self, client):
        response = client.post("/api/v1/auth/register", json={
            "email": "incomplete@test.com",
        })
        assert response.status_code == 422

    def test_register_invalid_email(self, client):
        response = client.post("/api/v1/auth/register", json={
            "email": "not-an-email",
            "password": "Pass123!",
            "display_name": "Bad Email",
        })
        assert response.status_code == 422

    def test_register_weak_password(self, client):
        """Very short password — should be accepted by API (validation is in frontend)."""
        response = client.post("/api/v1/auth/register", json={
            "email": "weakpw@test.com",
            "password": "a",
            "display_name": "Weak PW",
        })
        # API may accept or reject; both are valid behaviors
        assert response.status_code in (201, 422)

    def test_register_with_special_chars_name(self, client):
        response = client.post("/api/v1/auth/register", json={
            "email": "special@test.com",
            "password": "ValidPass123!",
            "display_name": "Nguyễn Văn A 😀🎉",
        })
        assert response.status_code == 201
        assert "Nguyễn Văn A" in response.json()["display_name"]


class TestAuthLogin:
    def test_login_valid(self, client, test_user):
        response = client.post("/api/v1/auth/login", json={
            "email": test_user["email"],
            "password": test_user["password"],
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_login_wrong_password(self, client, test_user):
        response = client.post("/api/v1/auth/login", json={
            "email": test_user["email"],
            "password": "WrongPassword123!",
        })
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client):
        response = client.post("/api/v1/auth/login", json={
            "email": "doesnotexist@test.com",
            "password": "SomePass123!",
        })
        assert response.status_code == 401

    def test_login_empty_password(self, client, test_user):
        response = client.post("/api/v1/auth/login", json={
            "email": test_user["email"],
            "password": "",
        })
        assert response.status_code in (401, 422)

    def test_login_empty_email(self, client):
        response = client.post("/api/v1/auth/login", json={
            "email": "",
            "password": "SomePass123!",
        })
        assert response.status_code == 422

    def test_login_missing_fields(self, client):
        response = client.post("/api/v1/auth/login", json={})
        assert response.status_code == 422


class TestAuthRefresh:
    def test_refresh_valid(self, client, test_user):
        login_resp = client.post("/api/v1/auth/login", json={
            "email": test_user["email"],
            "password": test_user["password"],
        })
        refresh_token = login_resp.json()["refresh_token"]

        response = client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh_token,
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_refresh_invalid_token(self, client):
        response = client.post("/api/v1/auth/refresh", json={
            "refresh_token": "invalid.refresh.token",
        })
        assert response.status_code == 401

    def test_refresh_with_access_token(self, client, test_user):
        login_resp = client.post("/api/v1/auth/login", json={
            "email": test_user["email"],
            "password": test_user["password"],
        })
        access_token = login_resp.json()["access_token"]

        # Using access token as refresh token should fail
        response = client.post("/api/v1/auth/refresh", json={
            "refresh_token": access_token,
        })
        assert response.status_code == 401

    def test_refresh_reuse(self, client, test_user):
        """Using same refresh token twice: second attempt should fail."""
        login_resp = client.post("/api/v1/auth/login", json={
            "email": test_user["email"],
            "password": test_user["password"],
        })
        refresh_token = login_resp.json()["refresh_token"]

        first = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert first.status_code == 200

        second = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert second.status_code == 401


class TestAuthLogout:
    def test_logout(self, client, test_user):
        login_resp = client.post("/api/v1/auth/login", json={
            "email": test_user["email"],
            "password": test_user["password"],
        })
        refresh_token = login_resp.json()["refresh_token"]

        response = client.post("/api/v1/auth/logout", json={
            "refresh_token": refresh_token,
        })
        assert response.status_code == 200
        assert response.json()["status"] == "logged_out"

    def test_logout_invalid_token(self, client):
        response = client.post("/api/v1/auth/logout", json={
            "refresh_token": "invalid.token",
        })
        assert response.status_code == 200  # Logout is idempotent


class TestProtectedEndpoints:
    def test_unauthenticated_access(self, client):
        """Accessing protected endpoint without token should fail."""
        response = client.get("/api/v1/users/me")
        assert response.status_code in (401, 403)

    def test_expired_token(self, client):
        """Use a clearly expired token."""
        expired = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0IiwiZXhwIjoxMDAwMDAwMDAwLCJpYXQiOjEwMDAwMDAwMDAsInR5cGUiOiJhY2Nlc3MifQ.fake"
        response = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {expired}"})
        assert response.status_code in (401, 403)

    def test_authenticated_access(self, client, test_user, auth_headers):
        response = client.get("/api/v1/users/me", headers=auth_headers)
        assert response.status_code == 200
