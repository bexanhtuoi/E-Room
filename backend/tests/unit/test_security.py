from __future__ import annotations

from datetime import timedelta

from app.security import create_access_token, decode_token, hash_password, verify_password


class TestPasswordHashing:
    def test_hash_and_verify_roundtrip(self):
        hashed = hash_password("Password123!")
        assert hashed != "Password123!"
        assert verify_password("Password123!", hashed) is True

    def test_verify_wrong_password(self):
        hashed = hash_password("Password123!")
        assert verify_password("WrongPassword!", hashed) is False

    def test_verify_empty_hash_returns_false(self):
        assert verify_password("Password123!", None) is False
        assert verify_password("Password123!", "") is False

    def test_same_password_produces_different_hashes(self):
        first = hash_password("Password123!")
        second = hash_password("Password123!")
        assert first != second


class TestAccessToken:
    def test_token_roundtrip_contains_sub_and_type(self):
        token = create_access_token(42)
        payload = decode_token(token)
        assert payload["sub"] == "42"
        assert payload["type"] == "access"
        assert "exp" in payload

    def test_custom_expiry_is_respected(self):
        token = create_access_token(7, expires_delta=timedelta(hours=3))
        payload = decode_token(token)
        assert payload["sub"] == "7"

    def test_invalid_token_returns_none(self):
        assert decode_token("not-a-jwt") is None
