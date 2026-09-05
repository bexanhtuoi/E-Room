from __future__ import annotations

import os
import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = "sqlite:///./test_eroom.db"
os.environ["SECRET_KEY"] = "test-secret-key-32-characters-minimum!"
os.environ["LIVEKIT_API_KEY"] = "testkey"
os.environ["LIVEKIT_API_SECRET"] = "test-secret-32-characters-long!!"

from app.main import app  # noqa: E402

PASSWORD = "Password123!"


def pytest_configure(config):
    config.addinivalue_line("markers", "requires_redis: Tests requiring a running Redis")


@pytest.fixture(scope="session")
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


def unique_email() -> str:
    return f"user_{uuid.uuid4().hex[:8]}@test.com"


def register(client: TestClient, email: str, full_name: str = "Test User") -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={"full_name": full_name, "email": email, "password": PASSWORD},
    )
    assert response.status_code == 201, response.text
    return response.json()


def login(client: TestClient, email: str) -> None:
    response = client.post("/api/v1/auth/login", data={"username": email, "password": PASSWORD})
    assert response.status_code == 200, response.text
    # Set cookie truc tiep cho TestClient session de cac request tiep theo gui cookie di
    token_cookie = response.cookies.get("access_token")
    if token_cookie:
        client.cookies.set("access_token", token_cookie)


@pytest.fixture
def alice(client: TestClient) -> dict:
    user = register(client, unique_email(), "Alice Tester")
    login(client, user["email"])
    return user


def make_user(client: TestClient, full_name: str = "Bob Tester") -> dict:
    user = register(client, unique_email(), full_name)
    return user


def switch_to(client: TestClient, user: dict) -> None:
    login(client, user["email"])


@pytest.fixture
def ai_mocks():
    with (
        patch("app.api.routers.message.enqueue_ai_job") as message_enqueue,
        patch("app.api.routers.room.enqueue_room_observer") as observer_enqueue,
        patch("app.api.routers.room.enqueue_room_transcriber") as transcriber_enqueue,
        patch("app.ai.tasks.enqueue_ai_job") as tasks_enqueue,
    ):
        message_enqueue.return_value = "mock-task-id"
        tasks_enqueue.return_value = "mock-task-id"
        yield {
            "message_enqueue": message_enqueue,
            "observer_enqueue": observer_enqueue,
            "transcriber_enqueue": transcriber_enqueue,
            "tasks_enqueue": tasks_enqueue,
        }


@pytest.fixture(scope="session")
def redis_available() -> bool:
    from app.integration.redis import ping

    return ping()
