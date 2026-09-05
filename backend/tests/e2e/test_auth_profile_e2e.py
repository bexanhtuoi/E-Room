from __future__ import annotations

from fastapi.testclient import TestClient

from app.models import EnglishLevel
from tests.conftest import unique_email


class TestAuthAndProfileE2E:
    def test_complete_user_lifecycle_e2e(self, client: TestClient):
        email = unique_email()
        password = "OriginalPassword123!"

        # 1. Dang ky tai khoan
        reg_res = client.post(
            "/api/v1/auth/register",
            json={"email": email, "full_name": "Lifecycle Tester", "password": password},
        )
        assert reg_res.status_code == 201
        user_data = reg_res.json()
        user_id = user_data["id"]

        # 2. Dang nhap lay token cookie
        login_res = client.post("/api/v1/auth/login", data={"username": email, "password": password})
        assert login_res.status_code == 200
        client.cookies.set("access_token", login_res.cookies.get("access_token"))

        # 3. Xem Profile ca nhan (GET /api/v1/users/me)
        me_res = client.get("/api/v1/users/me")
        assert me_res.status_code == 200
        assert me_res.json()["email"] == email

        # 4. Cap nhat Profile (English level, full name, avatar_url)
        update_res = client.patch(
            f"/api/v1/users/{user_id}",
            json={
                "full_name": "Updated Lifecycle Name",
                "english_level": EnglishLevel.C1,
                "avatar_url": "https://minio.eroom.app/avatars/user.png",
            },
        )
        assert update_res.status_code == 200
        assert update_res.json()["full_name"] == "Updated Lifecycle Name"
        assert update_res.json()["english_level"] == "C1"
        assert update_res.json()["avatar_url"] == "https://minio.eroom.app/avatars/user.png"

        # 5. Dang xuat (Logout)
        logout_res = client.post("/api/v1/auth/logout")
        assert logout_res.status_code == 200

        # 6. Kiem tra cookie da bi huy va khong con truy cap duoc /me
        client.cookies.clear()
        unauth_res = client.get("/api/v1/users/me")
        assert unauth_res.status_code == 403

        # 7. Dang nhap lai thanh cong
        relogin_res = client.post("/api/v1/auth/login", data={"username": email, "password": password})
        assert relogin_res.status_code == 200
