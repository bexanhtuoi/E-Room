from __future__ import annotations

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.database import engine
from app.models import RoleEnum
from app.services import user_crud
from tests.conftest import make_user, switch_to


class TestIDORAndOwnershipProtection:
    def test_cannot_update_other_user_profile(self, client: TestClient, alice: dict):
        bob = make_user(client, "Bob Tester")
        switch_to(client, alice)

        # Alice thu cap nhat profile cua Bob
        response = client.patch(
            f"/api/v1/users/{bob['id']}",
            json={"full_name": "Hacked Bob"},
        )
        assert response.status_code == 403

    def test_cannot_delete_other_user_room(self, client: TestClient, alice: dict):
        switch_to(client, alice)
        room = client.post("/api/v1/rooms/", json={"name": f"alice-room-{alice['id']}"}).json()
        assert "id" in room, room

        bob = make_user(client)
        switch_to(client, bob)

        # Bob thu xoa phong cua Alice
        response = client.delete(f"/api/v1/rooms/{room['id']}")
        assert response.status_code == 403

    def test_cannot_update_other_user_room(self, client: TestClient, alice: dict):
        switch_to(client, alice)
        room = client.post("/api/v1/rooms/", json={"name": f"alice-room-mod-{alice['id']}"}).json()
        assert "id" in room, room

        bob = make_user(client)
        switch_to(client, bob)

        # Bob thu sua phong cua Alice
        response = client.patch(f"/api/v1/rooms/{room['id']}", json={"name": "Hacked Room"})
        assert response.status_code == 403

    def test_cannot_delete_other_user_message(self, client: TestClient, alice: dict):
        switch_to(client, alice)
        room = client.post("/api/v1/rooms/", json={"name": f"alice-msg-room-{alice['id']}"}).json()
        assert "id" in room, room
        message = client.post(
            "/api/v1/messages/",
            json={"room_id": room["id"], "text": "Secret Message"},
        ).json()
        assert "id" in message, message

        bob = make_user(client)
        switch_to(client, bob)

        # Bob thu xoa message cua Alice
        response = client.delete(f"/api/v1/messages/{message['id']}")
        assert response.status_code == 403

    def test_cannot_delete_other_user_document(self, client: TestClient, alice: dict):
        switch_to(client, alice)
        doc = client.post(
            "/api/v1/documents/",
            json={"file_name": "a.pdf", "file_type": "pdf", "file_path": "minio/a.pdf"},
        ).json()
        assert "id" in doc, doc

        bob = make_user(client)
        switch_to(client, bob)

        # Bob thu xoa document cua Alice
        response = client.delete(f"/api/v1/documents/{doc['id']}")
        assert response.status_code == 403


class TestAdminRolePrivileges:
    def test_admin_can_update_any_resource(self, client: TestClient, alice: dict):
        # Set Alice thanh Admin trong DB
        with Session(engine) as db:
            db_alice = user_crud.get_one(db, id=alice["id"])
            db_alice.role = RoleEnum.admin
            user_crud.update(db, db_obj=db_alice, obj_in={"role": RoleEnum.admin})

        bob = make_user(client, "Bob Before Admin")
        switch_to(client, bob)
        bob_room = client.post("/api/v1/rooms/", json={"name": f"bob-room-{bob['id']}"}).json()
        assert "id" in bob_room, bob_room

        switch_to(client, alice)

        # Admin Alice cap nhat room cua Bob
        res = client.patch(f"/api/v1/rooms/{bob_room['id']}", json={"name": "Admin Moderated"})
        assert res.status_code == 200
        assert res.json()["name"] == "Admin Moderated"
