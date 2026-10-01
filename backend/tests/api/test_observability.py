from fastapi.testclient import TestClient


class TestMetrics:
    def test_metrics_endpoint_exposes_eroom_counters(self, client: TestClient):
        resp = client.get("/metrics")
        assert resp.status_code == 200
        assert "eroom_http_requests_total" in resp.text
        assert "eroom_http_request_duration_seconds" in resp.text

    def test_requests_increment_counter(self, client: TestClient):
        before = client.get("/metrics").text
        client.get("/api/v1/rooms/?public_only=true")
        after = client.get("/metrics").text
        assert len(after) >= len(before)
        assert "/api/v1/rooms/" in after


class TestTracingDisabledByDefault:
    def test_setup_tracing_returns_false_without_env(self):
        from app.integration.observability import setup_tracing

        assert setup_tracing() is False
