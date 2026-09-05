from __future__ import annotations

from fastapi.testclient import TestClient


class TestGoogleLogin:
    def test_login_without_config_redirects_to_login(self, client: TestClient):
        # Test env khong co GOOGLE_CLIENT_ID → dua browser ve login, khong crash
        response = client.get("/api/v1/auth/google/login", follow_redirects=False)
        assert response.status_code in (302, 307)
        assert "/login?google=error" in response.headers["location"]

    def test_login_redirects_to_google_when_configured(self, client: TestClient, monkeypatch):
        import app.api.routers.google_auth as google_auth

        monkeypatch.setattr(google_auth.settings, "google_client_id", "test-client-id.apps.googleusercontent.com")
        monkeypatch.setattr(google_auth.settings, "google_client_secret", "test-secret")
        monkeypatch.setattr(
            google_auth.settings,
            "google_redirect_uri",
            "https://localhost:3000/api/v1/auth/google/callback",
        )

        response = client.get("/api/v1/auth/google/login", follow_redirects=False)
        assert response.status_code in (302, 307)
        location = response.headers["location"]
        assert location.startswith("https://accounts.google.com/o/oauth2/v2/auth")
        assert "test-client-id" in location
        assert "openid" in location

    def test_callback_without_code_returns_422(self, client: TestClient):
        response = client.get("/api/v1/auth/google/callback")
        assert response.status_code == 422

    def test_callback_without_config_returns_400(self, client: TestClient):
        response = client.get("/api/v1/auth/google/callback?code=fake-code")
        assert response.status_code == 400
        assert "GOOGLE_CLIENT_ID" in response.json()["detail"]
