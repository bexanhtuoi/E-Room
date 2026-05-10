from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))


def test_health_endpoint(client):
    r = client.get("/api/v1/health")
    assert r.status_code in (200, 404)

def test_api_docs(client):
    r = client.get("/docs")
    assert r.status_code == 200

def test_openapi_schema(client):
    r = client.get("/openapi.json")
    assert r.status_code == 200
    assert "openapi" in r.json()
