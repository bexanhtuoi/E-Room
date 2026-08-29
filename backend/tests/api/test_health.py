from __future__ import annotations

from fastapi.testclient import TestClient


class TestHealth:
    def test_health_returns_200_and_healthy(self, client: TestClient):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"] == "ok"

    def test_api_docs_available(self, client: TestClient):
        response = client.get("/docs")
        assert response.status_code == 200

    def test_unknown_route_returns_404(self, client: TestClient):
        response = client.get("/api/v1/does-not-exist")
        assert response.status_code == 404
