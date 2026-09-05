from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import make_user, switch_to


class TestGetUsers:
    def test_count_returns_int(self, client: TestClient, alice: dict):
        response = client.get("/api/v1/users/count")
        assert response.status_code == 200
        assert isinstance(response.json()["count"], int)
        assert response.json()["count"] >= 1

    def test_get_user_by_id(self, client: TestClient, alice: dict):
        response = client.get(f"/api/v1/users/{alice['id']}")
        assert response.status_code == 200
        assert response.json()["email"] == alice["email"]

    def test_get_unknown_user_returns_404(self, client: TestClient, alice: dict):
        assert client.get("/api/v1/users/999999").status_code == 404

    def test_get_user_by_email(self, client: TestClient, alice: dict):
        response = client.get(f"/api/v1/users/email/{alice['email']}")
        assert response.status_code == 200
        assert response.json()["id"] == alice["id"]

    def test_get_user_by_unknown_email_returns_404(self, client: TestClient, alice: dict):
        assert client.get("/api/v1/users/email/nobody@test.com").status_code == 404

    def test_get_users_by_role_contains_registered_user(self, client: TestClient, alice: dict):
        response = client.get("/api/v1/users/role/user")
        assert response.status_code == 200
        emails = [u["email"] for u in response.json()]
        assert alice["email"] in emails

    def test_list_users_respects_limit(self, client: TestClient, alice: dict):
        response = client.get("/api/v1/users/?limit=2")
        assert response.status_code == 200
        assert len(response.json()) <= 2


class TestUpdateUser:
    def test_update_own_profile(self, client: TestClient, alice: dict):
        response = client.patch(
            f"/api/v1/users/{alice['id']}",
            json={"full_name": "Alice Updated", "english_level": "B2"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Alice Updated"
        assert data["english_level"] == "B2"

    def test_update_invalid_english_level_returns_422(self, client: TestClient, alice: dict):
        response = client.patch(f"/api/v1/users/{alice['id']}", json={"english_level": "Z9"})
        assert response.status_code == 422

    def test_update_other_user_returns_403(self, client: TestClient, alice: dict):
        bob = make_user(client)
        switch_to(client, bob)
        response = client.patch(f"/api/v1/users/{alice['id']}", json={"full_name": "Hacked"})
        assert response.status_code == 403
        switch_to(client, alice)


class TestDeleteUser:
    def test_delete_self_cascades_rooms_and_messages(self, client: TestClient):
        temp = make_user(client, "Temp User")
        switch_to(client, temp)

        room = client.post(
            "/api/v1/rooms/",
            json={"name": f"cascade-room-{temp['id']}"},
        ).json()
        client.post(
            "/api/v1/messages/",
            json={"room_id": room["id"], "text": "will be removed", "role": "user"},
        )

        deleted = client.delete(f"/api/v1/users/{temp['id']}")
        assert deleted.status_code == 200
        assert deleted.json()["email"] == temp["email"]

        assert client.get(f"/api/v1/rooms/{room['id']}").status_code == 404
        remaining = client.get(f"/api/v1/messages/?room_id={room['id']}").json()
        assert remaining == []

    def test_delete_other_user_returns_403(self, client: TestClient, alice: dict):
        bob = make_user(client)
        switch_to(client, bob)
        assert client.delete(f"/api/v1/users/{alice['id']}").status_code == 403
        switch_to(client, alice)

    def test_deleted_user_cannot_authenticate_anymore(self, client: TestClient):
        from tests.conftest import PASSWORD

        temp = make_user(client, "Vanishing")
        switch_to(client, temp)
        client.delete(f"/api/v1/users/{temp['id']}")

        relogin = client.post("/api/v1/auth/login", data={"username": temp["email"], "password": PASSWORD})
        assert relogin.status_code == 400
