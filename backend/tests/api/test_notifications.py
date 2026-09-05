from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import make_user, switch_to


def create_notification(client: TestClient, title: str, body: str | None = None, ntype: str = "system") -> dict:
    payload: dict = {"title": title, "notification_type": ntype}
    if body is not None:
        payload["body"] = body
    response = client.post("/api/v1/notifications/", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


class TestNotificationCrud:
    def test_create_defaults_to_current_user(self, client: TestClient, alice: dict):
        notification = create_notification(client, "Welcome", "Hello Alice")
        assert notification["user_id"] == alice["id"]
        assert notification["is_read"] is False
        assert notification["notification_type"] == "system"

    def test_list_returns_only_own_notifications(self, client: TestClient, alice: dict):
        create_notification(client, "Alice Only")
        bob = make_user(client)
        switch_to(client, bob)
        create_notification(client, "Bob Private")

        switch_to(client, alice)
        listed = client.get("/api/v1/notifications/?limit=50").json()
        titles = [n["title"] for n in listed]
        assert "Alice Only" in titles
        assert "Bob Private" not in titles

    def test_count_scoped_to_current_user(self, client: TestClient, alice: dict):
        create_notification(client, "Count One")
        count = client.get("/api/v1/notifications/count").json()["count"]
        assert count >= 1

    def test_mark_as_read(self, client: TestClient, alice: dict):
        notification = create_notification(client, "Mark me")
        updated = client.patch(f"/api/v1/notifications/{notification['id']}", json={"is_read": True})
        assert updated.status_code == 200
        assert updated.json()["is_read"] is True

    def test_update_other_users_notification_returns_403(self, client: TestClient, alice: dict):
        notification = create_notification(client, "Alice secret")
        bob = make_user(client)
        switch_to(client, bob)
        response = client.patch(f"/api/v1/notifications/{notification['id']}", json={"is_read": True})
        assert response.status_code == 403
        switch_to(client, alice)

    def test_delete_own_notification(self, client: TestClient, alice: dict):
        notification = create_notification(client, "Delete me")
        deleted = client.delete(f"/api/v1/notifications/{notification['id']}")
        assert deleted.status_code == 200
        assert client.get(f"/api/v1/notifications/{notification['id']}").status_code in (404, 405)

    def test_delete_other_users_notification_returns_403(self, client: TestClient, alice: dict):
        notification = create_notification(client, "Stay here")
        bob = make_user(client)
        switch_to(client, bob)
        assert client.delete(f"/api/v1/notifications/{notification['id']}").status_code == 403
        switch_to(client, alice)

    def test_unknown_notification_returns_404(self, client: TestClient, alice: dict):
        assert client.patch("/api/v1/notifications/999999", json={"is_read": True}).status_code == 404
