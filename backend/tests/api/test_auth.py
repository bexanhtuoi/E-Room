from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import PASSWORD, login, make_user, unique_email


class TestRegister:
    def test_register_success(self, client: TestClient):
        email = unique_email()
        response = client.post(
            "/api/v1/auth/register",
            json={"full_name": "New User", "email": email, "password": PASSWORD},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == email
        assert data["full_name"] == "New User"
        assert data["role"] == "user"

    def test_register_does_not_leak_password_fields(self, client: TestClient):
        response = client.post(
            "/api/v1/auth/register",
            json={"full_name": "Leak Check", "email": unique_email(), "password": PASSWORD},
        )
        data = response.json()
        assert "password" not in data
        assert "password_hash" not in data

    def test_register_duplicate_email_returns_400(self, client: TestClient):
        user = make_user(client)
        response = client.post(
            "/api/v1/auth/register",
            json={"full_name": "Dup", "email": user["email"], "password": PASSWORD},
        )
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]

    def test_register_weak_password_returns_422(self, client: TestClient):
        response = client.post(
            "/api/v1/auth/register",
            json={"full_name": "Weak", "email": unique_email(), "password": "short"},
        )
        assert response.status_code == 422


class TestLogin:
    def test_login_success_sets_httponly_cookie(self, client: TestClient):
        user = make_user(client)
        response = client.post("/api/v1/auth/login", data={"username": user["email"], "password": PASSWORD})
        assert response.status_code == 200
        cookie = response.cookies.get("access_token")
        assert cookie

    def test_login_wrong_password_returns_400(self, client: TestClient):
        user = make_user(client)
        response = client.post("/api/v1/auth/login", data={"username": user["email"], "password": "WrongPass123!"})
        assert response.status_code == 400

    def test_login_unknown_email_returns_400(self, client: TestClient):
        response = client.post("/api/v1/auth/login", data={"username": "ghost@test.com", "password": PASSWORD})
        assert response.status_code == 400


class TestMe:
    def test_me_returns_current_user(self, client: TestClient, alice: dict):
        response = client.get("/api/v1/users/me")
        assert response.status_code == 200
        assert response.json()["email"] == alice["email"]

    def test_me_without_cookie_returns_403(self):
        raw_client = TestClient(app)
        response = raw_client.get("/api/v1/users/me")
        assert response.status_code == 403


class TestLogout:
    def test_logout_invalidates_session(self, client: TestClient):
        user = make_user(client)
        login(client, user["email"])
        logout = client.post("/api/v1/auth/logout")
        assert logout.status_code == 200

        fresh_client = TestClient(app)
        me_after = fresh_client.get("/api/v1/users/me")
        assert me_after.status_code == 403


class TestIdentitySwitch:
    def test_switch_user_updates_identity(self, client: TestClient, alice: dict):
        bob = make_user(client)
        login(client, bob["email"])
        assert client.get("/api/v1/users/me").json()["email"] == bob["email"]
        login(client, alice["email"])
        assert client.get("/api/v1/users/me").json()["email"] == alice["email"]
