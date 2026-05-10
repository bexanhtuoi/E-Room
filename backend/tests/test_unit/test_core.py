from __future__ import annotations

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))


class TestConfig:
    def test_settings_exist(self):
        from app.config import settings
        assert settings.app_name == "E-Room API"
        assert settings.llm_base_url == "http://localhost:20128/v1"
        assert settings.llm_model.startswith("ds2api/deepseek")
        assert len(settings.llm_api_key) > 10

    def test_secret_key_set(self):
        from app.config import settings
        if settings.app_env != "development":
            assert "change-me" not in settings.secret_key.lower()


class TestSecurity:
    def test_hash_and_verify(self):
        from app.security import hash_password, verify_password
        h = hash_password("mysecret")
        assert h != "mysecret"
        assert verify_password("mysecret", h)
        assert not verify_password("wrong", h)

    def test_create_access_token(self):
        from app.security import create_access_token
        t = create_access_token("uid-1")
        assert isinstance(t, str)
        assert t.count(".") == 2

    def test_decode_valid(self):
        from app.security import create_access_token, decode_token
        t = create_access_token("uid-1")
        p = decode_token(t)
        assert p and p.get("sub") == "uid-1"

    def test_decode_invalid(self):
        from app.security import decode_token
        assert decode_token("bad.token") is None


class TestAudioBuffer:
    def test_construct(self):
        from app.infrastructure.audio import AudioBuffer, AudioConfig
        b = AudioBuffer("u1", AudioConfig())
        assert b.user_id == "u1"
        assert b.config.sample_rate == 16000

    def test_silent_chunk(self):
        from app.infrastructure.audio import AudioBuffer, AudioConfig
        b = AudioBuffer("u2", AudioConfig(rms_threshold=0.80))
        assert b.feed_chunk(0, b"\x00" * 640) is None

    def test_loud_speech_start(self):
        from app.infrastructure.audio import AudioBuffer, AudioConfig
        b = AudioBuffer("u3", AudioConfig(rms_threshold=0.01))
        assert b.feed_chunk(0, b"\x00\x80" * 320) == "speech_start"

    def test_reset(self):
        from app.infrastructure.audio import AudioBuffer, AudioConfig
        b = AudioBuffer("u4", AudioConfig(rms_threshold=0.01))
        b.feed_chunk(0, b"\x00\x80" * 320)
        b.reset()
        assert b.get_sentence() == b""


class TestAgentImports:
    def test_corrector(self):
        from app.agent import AgentCorrector
        a = AgentCorrector()
        assert a._llm_base

    def test_expert(self):
        from app.agent import AgentExpert
        a = AgentExpert()
        assert a._llm_base

    def test_heartbeat(self):
        from app.agent import AgentHeartbeat
        a = AgentHeartbeat()
        assert a._llm_base


class TestRAGImports:
    def test_chunker(self):
        from app.rag import TextChunker
        c = TextChunker(chunk_size=512, chunk_overlap=64)
        chunks = c.chunk_text("hello world " * 300)
        assert len(chunks) > 1

    def test_embedding_service(self):
        from app.rag import EmbeddingService
        s = EmbeddingService()
        assert s._model == "text-embedding-3-small"

    def test_vector_store_tmp(self):
        from app.rag import VectorStore
        v = VectorStore()
        v.store_embeddings([{"embedding": [0.1] * 10, "text": "hi"}])
        r = v.similarity_search([0.1] * 10, top_k=1)
        assert len(r) == 1 and r[0]["text"] == "hi"

    def test_file_handler(self):
        from app.rag import FileHandler
        h = FileHandler()
        assert h.is_supported("a.txt")
        assert h.is_supported("b.pdf")
        assert not h.is_supported("c.mp4")
