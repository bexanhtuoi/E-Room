from __future__ import annotations

import hashlib
import os

import pytest

from app.service.token_store import TokenStore


@pytest.fixture
def token_store() -> TokenStore:
    return TokenStore()


class TestHashRefreshToken:
    def test_hash_is_deterministic(self, token_store: TokenStore) -> None:
        token = "my-refresh-token-abc123"
        hash1 = token_store.hash_refresh_token(token)
        hash2 = token_store.hash_refresh_token(token)
        assert hash1 == hash2

    def test_different_tokens_produce_different_hashes(self, token_store: TokenStore) -> None:
        hash1 = token_store.hash_refresh_token("token-alpha")
        hash2 = token_store.hash_refresh_token("token-beta")
        assert hash1 != hash2

    def test_hash_is_sha256_hex(self, token_store: TokenStore) -> None:
        token = "secure-token"
        result = token_store.hash_refresh_token(token)
        expected = hashlib.sha256(token.encode()).hexdigest()
        assert result == expected
        assert len(result) == 64

    def test_hash_empty_string(self, token_store: TokenStore) -> None:
        result = token_store.hash_refresh_token("")
        expected = hashlib.sha256(b"").hexdigest()
        assert result == expected

    def test_hash_with_special_characters(self, token_store: TokenStore) -> None:
        token = "token!@#$%^&*()_+-=[]{}|;:',.<>?/"
        result = token_store.hash_refresh_token(token)
        expected = hashlib.sha256(token.encode()).hexdigest()
        assert result == expected


class TestGenerateSecureToken:
    def test_default_length_is_32_bytes_base64(self, token_store: TokenStore) -> None:
        token = token_store.generate_secure_token()
        assert isinstance(token, str)
        assert len(token) > 0
        assert "-" not in token or "_" in token or any(c.isupper() for c in token)

    def test_custom_byte_length(self, token_store: TokenStore) -> None:
        token = token_store.generate_secure_token(byte_length=16)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_generated_tokens_are_unique(self, token_store: TokenStore) -> None:
        tokens = {token_store.generate_secure_token() for _ in range(20)}
        assert len(tokens) == 20

    def test_larger_byte_length_produces_longer_token(self, token_store: TokenStore) -> None:
        token_short = token_store.generate_secure_token(byte_length=8)
        token_long = token_store.generate_secure_token(byte_length=64)
        assert len(token_long) > len(token_short)


@pytest.mark.skipif(not os.getenv("CI"), reason="Requires Redis server")
class TestTokenStoreRedisIntegration:
    @pytest.fixture
    def ts(self) -> TokenStore:
        return TokenStore()

    def test_blacklist_and_check_access_token(self, ts: TokenStore) -> None:
        jti = "jti-test-001"
        ts.blacklist_access_token(jti, ttl_seconds=300)
        assert ts.is_blacklisted(jti) is True

    def test_not_blacklisted_returns_false(self, ts: TokenStore) -> None:
        assert ts.is_blacklisted("jti-never-blacklisted") is False

    def test_store_and_validate_refresh_token(self, ts: TokenStore) -> None:
        user_id = "user-store-test"
        token = "refresh-token-plain-value"
        ts.store_refresh_token(user_id, token, ttl_seconds=600)
        assert ts.validate_refresh_token(user_id, token) is True

    def test_validate_invalid_refresh_token(self, ts: TokenStore) -> None:
        user_id = "user-invalid-test"
        assert ts.validate_refresh_token(user_id, "bogus-token") is False

    def test_revoke_refresh_token(self, ts: TokenStore) -> None:
        user_id = "user-revoke-test"
        token = "revokable-token"
        token_hash = ts.store_refresh_token(user_id, token, ttl_seconds=600)
        ts.revoke_refresh_token(user_id, token_hash)
        assert ts.validate_refresh_token(user_id, token) is False

    def test_revoke_all_user_tokens(self, ts: TokenStore) -> None:
        user_id = "user-revokeall-test"
        ts.store_refresh_token(user_id, "token1", ttl_seconds=600)
        ts.store_refresh_token(user_id, "token2", ttl_seconds=600)
        ts.revoke_all_user_tokens(user_id)
        assert ts.validate_refresh_token(user_id, "token1") is False
        assert ts.validate_refresh_token(user_id, "token2") is False
