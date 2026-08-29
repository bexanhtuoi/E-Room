from __future__ import annotations

from fastapi.testclient import TestClient

from sqlmodel import Session

from app.database import engine
from app.models import RoleEnum, User
from tests.conftest import make_user, switch_to


def create_document(client: TestClient, name: str) -> dict:
    response = client.post(
        "/api/v1/documents/",
        json={"file_name": name, "file_type": "pdf", "file_path": f"documents/{name}"},
    )
    assert response.status_code == 201, response.text
    return response.json()


class TestDocumentCrud:
    def test_create_binds_current_user(self, client: TestClient, alice: dict):
        document = create_document(client, f"doc-{alice['id']}.pdf")
        assert document["user_id"] == alice["id"]
        assert document["file_name"] == f"doc-{alice['id']}.pdf"

    def test_list_and_count(self, client: TestClient, alice: dict):
        create_document(client, f"counted-{alice['id']}.pdf")
        listed = client.get("/api/v1/documents/?limit=50").json()
        assert any(d["file_name"] == f"counted-{alice['id']}.pdf" for d in listed)
        assert client.get("/api/v1/documents/count").json()["count"] >= 1

    def test_get_by_id_and_404(self, client: TestClient, alice: dict):
        document = create_document(client, f"single-{alice['id']}.pdf")
        fetched = client.get(f"/api/v1/documents/{document['id']}")
        assert fetched.status_code == 200
        assert client.get("/api/v1/documents/999999").status_code == 404

    def test_update_own_document(self, client: TestClient, alice: dict):
        document = create_document(client, f"upd-{alice['id']}.pdf")
        updated = client.patch(
            f"/api/v1/documents/{document['id']}",
            json={"file_name": "renamed.pdf", "metadata_json": '{"pages": 3}'},
        )
        assert updated.status_code == 200
        assert updated.json()["file_name"] == "renamed.pdf"
        assert updated.json()["metadata_json"] == '{"pages": 3}'

    def test_update_other_users_document_returns_403(self, client: TestClient, alice: dict):
        document = create_document(client, f"locked-{alice['id']}.pdf")
        bob = make_user(client)
        switch_to(client, bob)
        response = client.patch(f"/api/v1/documents/{document['id']}", json={"file_name": "steal.pdf"})
        assert response.status_code == 403
        switch_to(client, alice)

    def test_admin_can_delete_other_users_document(self, client: TestClient, alice: dict):
        document = create_document(client, f"admin-del-{alice['id']}.pdf")

        admin = make_user(client, "Admin Guy")
        with Session(engine) as db:
            user = db.get(User, int(admin["id"]))
            user.role = RoleEnum.admin
            db.add(user)
            db.commit()

        switch_to(client, admin)
        deleted = client.delete(f"/api/v1/documents/{document['id']}")
        assert deleted.status_code == 200
        switch_to(client, alice)

    def test_non_admin_delete_other_users_document_returns_403(self, client: TestClient, alice: dict):
        document = create_document(client, f"safe-{alice['id']}.pdf")
        bob = make_user(client)
        switch_to(client, bob)
        assert client.delete(f"/api/v1/documents/{document['id']}").status_code == 403
        switch_to(client, alice)

    def test_delete_unknown_returns_404(self, client: TestClient, alice: dict):
        assert client.delete("/api/v1/documents/999999").status_code == 404
