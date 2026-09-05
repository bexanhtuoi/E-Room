from __future__ import annotations

import time
from datetime import timedelta

import jwt
from fastapi.testclient import TestClient

from app.security import create_access_token, decode_token, hash_password, verify_password


class TestJWTSecurity:
    def test_reject_algorithm_none(self, client: TestClient):
        # Thu nghiem tan cong JWT voi header alg: none
        payload = {"sub": "1", "type": "access", "exp": int(time.time()) + 3600}
        insecure_token = jwt.encode(payload, key="", algorithm="none")

        decoded = decode_token(insecure_token)
        assert decoded is None

        # Thu gui len API kem cookie gia mao nay
        client.cookies.set("access_token", insecure_token)
        response = client.get("/api/v1/users/me")
        assert response.status_code == 403

    def test_reject_wrong_secret_key(self, client: TestClient):
        # Ky token bang secret key gia mao (it nhat 32 ky tu)
        payload = {"sub": "1", "type": "access", "exp": int(time.time()) + 3600}
        fake_token = jwt.encode(payload, "malicious-secret-key-1234567890123456", algorithm="HS256")

        decoded = decode_token(fake_token)
        assert decoded is None

        client.cookies.set("access_token", fake_token)
        response = client.get("/api/v1/users/me")
        assert response.status_code == 403

    def test_reject_expired_token(self, client: TestClient):
        # Token het han
        expired_token = create_access_token(data=1, expires_delta=timedelta(seconds=-10))
        decoded = decode_token(expired_token)
        assert decoded is None

        client.cookies.set("access_token", expired_token)
        response = client.get("/api/v1/users/me")
        assert response.status_code == 403

    def test_reject_tampered_payload(self):
        token = create_access_token(data=1)
        # Thay doi chuoi token o phan payload
        parts = token.split(".")
        tampered_token = f"{parts[0]}.eyAic3ViIjogIjIiLCJ0eXBlIjoiYWNjZXNzIiwiZXhwIjoxODAwMDAwMDAwfQ.{parts[2]}"
        assert decode_token(tampered_token) is None


class TestPasswordSecurity:
    def test_password_hashing_robustness(self):
        password = "VeryComplexPassword#@2026!"
        hashed = hash_password(password)

        assert hashed != password
        assert verify_password(password, hashed) is True
        assert verify_password(password + "a", hashed) is False

    def test_verify_wrong_password_edge_cases(self):
        hashed = hash_password("valid_pwd")
        assert verify_password("wrong_pwd", hashed) is False
        assert verify_password("", hashed) is False
        assert verify_password("valid_pwd", "") is False
        assert verify_password("valid_pwd", None) is False
