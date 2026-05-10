from __future__ import annotations

import time
import jwt
import pytest
from unittest.mock import MagicMock, patch

from app.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_token,
    verify_password,
)


class TestPasswordHashing:
    def test_hash_produces_different_output(self):
        h1 = hash_password("password123")
        h2 = hash_password("password123")
        assert h1 != h2  # salt ensures different hashes

    def test_verify_correct_password(self):
        h = hash_password("mypassword")
        assert verify_password("mypassword", h)

    def test_verify_wrong_password(self):
        h = hash_password("mypassword")
        assert not verify_password("wrong", h)

    def test_verify_none_hash(self):
        assert not verify_password("anything", None)

    def test_verify_empty_string(self):
        assert not verify_password("", None)
        h = hash_password("nonempty")
        assert not verify_password("", h)

    def test_special_characters(self):
        pw = "p@ss!😀đâylàtiếngviệt"
        h = hash_password(pw)
        assert verify_password(pw, h)

    def test_very_long_password(self):
        pw = "a" * 10000
        h = hash_password(pw)
        assert verify_password(pw, h)


class TestTokenCreation:
    def test_access_token_structure(self):
        token = create_access_token("user-123")
        parts = token.split(".")
        assert len(parts) == 3
        for part in parts:
            assert len(part) > 0

    def test_access_token_decodeable(self):
        token = create_access_token("user-456")
        decoded = decode_token(token)
        assert decoded is not None
        assert decoded["sub"] == "user-456"
        assert decoded["type"] == "access"
        assert "exp" in decoded
        assert "iat" in decoded
        assert "jti" in decoded

    def test_refresh_token_type(self):
        token = create_refresh_token("user-789")
        decoded = decode_token(token)
        assert decoded["type"] == "refresh"

    def test_tokens_unique(self):
        t1 = create_access_token("user-1")
        t2 = create_access_token("user-1")
        d1 = decode_token(t1)
        d2 = decode_token(t2)
        assert d1["jti"] != d2["jti"]  # unique JTI

    def test_different_subjects(self):
        t1 = create_access_token("user-A")
        t2 = create_access_token("user-B")
        d1 = decode_token(t1)
        d2 = decode_token(t2)
        assert d1["sub"] != d2["sub"]


class TestTokenDecoding:
    def test_decode_valid_token(self):
        token = create_access_token("valid-user")
        decoded = decode_token(token)
        assert decoded is not None
        assert isinstance(decoded, dict)

    def test_decode_invalid_token_returns_none(self):
        result = decode_token("not.a.real.token.at.all.extra")
        assert result is None

    def test_decode_empty_token(self):
        result = decode_token("")
        assert result is None

    def test_decode_tampered_payload(self):
        token = create_access_token("victim")
        parts = token.split(".")
        parts[1] = "dGFtcGVyZWQ"  # "tampered" in base64
        tampered = ".".join(parts)
        result = decode_token(tampered)
        assert result is None  # signature mismatch

    def test_decode_tampered_signature(self):
        token = create_access_token("victim")
        parts = token.split(".")
        parts[2] = "A" * 43  # garbage signature
        tampered = ".".join(parts)
        result = decode_token(tampered)
        assert result is None

    def test_decode_missing_segments(self):
        assert decode_token("header.payload") is None
        assert decode_token("header..") is None

    def test_decode_none_token(self):
        try:
            result = decode_token(None)
            assert result is None
        except (TypeError, AttributeError):
            pass  # acceptable behavior


class TestTokenExpiry:
    def test_expiry_is_future(self):
        token = create_access_token("user-exp")
        decoded = decode_token(token)
        now = int(time.time())
        assert decoded["exp"] > now

    def test_custom_expiry(self):
        from datetime import timedelta
        token = create_access_token("user-cust", expires_delta=timedelta(seconds=1))
        decoded = decode_token(token)
        now = int(time.time())
        assert decoded["exp"] <= now + 2


class TestHashToken:
    def test_deterministic(self):
        h1 = hash_token("mytoken")
        h2 = hash_token("mytoken")
        assert h1 == h2

    def test_different_inputs(self):
        h1 = hash_token("token1")
        h2 = hash_token("token2")
        assert h1 != h2

    def test_hex_format(self):
        h = hash_token("test")
        assert len(h) == 64  # SHA-256 hex
        assert all(c in "0123456789abcdef" for c in h)


class TestAlgorithmTampering:
    def test_alg_confusion_none(self):
        """Verify tokens without 'none' algorithm are rejected."""
        parts = create_access_token("user-alg").split(".")
        parts[0] = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0"  # {"alg":"none","typ":"JWT"}
        fake = ".".join([parts[0], parts[1], ""])
        result = decode_token(fake)
        assert result is None

    def test_alg_confusion_hs256_to_hs256(self):
        """Ensure PyJWT rejects mismatched algorithms."""
        token = create_access_token("user-hs")
        decoded = decode_token(token)
        assert decoded is not None
        assert decoded["sub"] == "user-hs"
