from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from unittest.mock import MagicMock, patch

from app.api.dependencies import get_db_session
from app.api.routers.infra import rate_limit_login
from app.main import app
from app.model.user import User
from app.security import hash_password


TEST_DATABASE_URL = "sqlite:///./test_eroom.db"


@pytest.fixture(scope="session")
def engine():
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False}, echo=False)
    SQLModel.metadata.create_all(engine)
    yield engine
    # Clean up test DB after all tests
    import os
    try:
        os.remove("./test_eroom.db")
    except OSError:
        pass


@pytest.fixture(scope="function")
def db_session(engine):
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db_session):
    def override_get_session():
        yield db_session

    async def override_rate_limit(request=None):
        pass  # no-op in tests — Redis may not be available

    app.dependency_overrides[get_db_session] = override_get_session
    app.dependency_overrides[rate_limit_login] = override_rate_limit
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db_session):
    user = User(
        email="test@example.com",
        password_hash=hash_password("password123"),
        display_name="Test User",
        english_level="B1",
        learning_goal="Improve speaking",
        profile_completed=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return {"id": str(user.id), "email": user.email, "password": "password123", "display_name": user.display_name}


@pytest.fixture
def auth_headers(client, test_user):
    response = client.post("/api/v1/auth/login", json={"email": test_user["email"], "password": test_user["password"]})
    if response.status_code == 200:
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    return {"Authorization": "Bearer fake-token"}


@pytest.fixture
def mock_redis():
    with patch("app.infrastructure.redis.RedisCRUD") as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_livekit():
    with patch("app.infrastructure.livekit.LiveKitService") as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        yield mock_instance
