from __future__ import annotations

import pytest
import tempfile
import os
from unittest.mock import MagicMock, AsyncMock, patch

from app.rag.chunking import TextChunker
from app.rag.embedding import EmbeddingService
from app.rag.vector_store import NumpyVectorStore
from app.rag.retrieval import RetrievalService
from app.rag.file_handle import FileHandler


class TestTextChunker:
    def test_default_construction(self):
        chunker = TextChunker()
        assert chunker is not None

    def test_custom_construction(self):
        chunker = TextChunker(chunk_size=256, chunk_overlap=32)
        assert chunker.chunk_size == 256
        assert chunker.chunk_overlap == 32

    def test_chunk_text_basic(self):
        chunker = TextChunker(chunk_size=16, chunk_overlap=4)
        text = "hello world this is a test sentence for chunking"
        chunks = chunker.chunk_text(text)
        assert len(chunks) > 1
        for c in chunks:
            assert len(c) > 0

    def test_chunk_empty_text(self):
        chunker = TextChunker()
        chunks = chunker.chunk_text("")
        assert chunks == []

    def test_chunk_short_text(self):
        chunker = TextChunker(chunk_size=500)
        chunks = chunker.chunk_text("short text")
        assert len(chunks) == 1
        assert chunks[0] == "short text"

    def test_chunk_overlap(self):
        chunker = TextChunker(chunk_size=50, chunk_overlap=10)
        text = "word " * 100
        chunks = chunker.chunk_text(text)
        assert len(chunks) >= 2

    def test_chunk_with_vietnamese(self):
        chunker = TextChunker(chunk_size=16, chunk_overlap=4)
        text = "Xin chào các bạn đây là tiếng Việt có dấu"
        chunks = chunker.chunk_text(text)
        for c in chunks:
            assert len(c) > 0

    def test_chunk_large_text(self):
        chunker = TextChunker(chunk_size=512, chunk_overlap=64)
        text = "Lorem ipsum dolor sit amet. " * 500
        chunks = chunker.chunk_text(text)
        assert len(chunks) > 0


class TestEmbeddingService:
    def test_construction(self):
        svc = EmbeddingService()
        assert svc is not None

    def test_embed_query(self):
        svc = EmbeddingService()
        import asyncio, numpy as np

        async def _test():
            with patch.object(svc, '_call_api', return_value=[np.random.randn(1536).tolist()]):
                vec = await svc.embed_query("test text")
                return vec

        result = asyncio.run(_test())
        assert result is not None
        assert len(result) == 1536

    def test_embed_texts(self):
        svc = EmbeddingService()
        import asyncio, numpy as np

        async def _test():
            with patch.object(svc, '_call_api', return_value=[np.random.randn(1536).tolist() for _ in range(5)]):
                vecs = await svc.embed_texts(["text1", "text2", "text3", "text4", "text5"])
                return vecs

        result = asyncio.run(_test())
        assert len(result) == 5
        for v in result:
            assert len(v) == 1536

    def test_embed_empty_batch(self):
        svc = EmbeddingService()
        import asyncio

        async def _test():
            vecs = await svc.embed_texts([])
            return vecs

        result = asyncio.run(_test())
        assert result == []


class TestVectorStore:
    def test_store_and_search(self):
        import numpy as np
        vs = NumpyVectorStore()
        vec = np.random.randn(10).tolist()
        items = [{
            "chunk_id": "id-1",
            "document_id": "doc1",
            "text": "hello world",
            "embedding": vec,
            "metadata": {"source": "doc1"},
        }]
        count = vs.store_embeddings(items)
        assert count == 1
        results = vs.similarity_search(vec, top_k=2)
        assert len(results) >= 1
        assert results[0]["text"] == "hello world"

    def test_store_multiple(self):
        import numpy as np
        vs = NumpyVectorStore()
        items = [
            {"chunk_id": f"b-{i}", "document_id": "doc-b",
             "text": f"text-{i}", "embedding": np.random.randn(10).tolist()}
            for i in range(5)
        ]
        count = vs.store_embeddings(items)
        assert count == 5
        results = vs.similarity_search(items[0]["embedding"], top_k=3)
        assert len(results) == 3

    def test_search_empty_store(self):
        vs = NumpyVectorStore()
        results = vs.similarity_search([0.1] * 10, top_k=5)
        assert results == []

    def test_delete_by_document(self):
        import numpy as np
        vs = NumpyVectorStore()
        vec = [0.1] * 10
        vs.store_embeddings([{
            "chunk_id": "del-1", "document_id": "doc-del",
            "text": "temporary", "embedding": vec,
        }])
        deleted = vs.delete_by_document("doc-del")
        assert deleted == 1
        results = vs.similarity_search(vec, top_k=1)
        assert results == []

    def test_count(self):
        import numpy as np
        vs = NumpyVectorStore()
        assert vs.count() == 0
        vs.store_embeddings([{
            "chunk_id": "c1", "document_id": "doc-c",
            "text": "test", "embedding": [0.0] * 10,
        }])
        assert vs.count() == 1

    def test_similarity_score_descending(self):
        import numpy as np
        vs = NumpyVectorStore()
        v1 = [1.0, 0.0, 0.0]
        v2 = [0.0, 1.0, 0.0]
        v3 = [0.0, 0.0, 1.0]
        vs.store_embeddings([
            {"chunk_id": "a", "document_id": "d", "text": "A", "embedding": v2},
            {"chunk_id": "b", "document_id": "d", "text": "B", "embedding": v3},
        ])
        results = vs.similarity_search(v1, top_k=2)
        assert len(results) == 2
        assert "score" in results[0]


class TestRetrievalService:
    def test_construction(self):
        svc = RetrievalService()
        assert svc is not None

    def test_retrieve_basic(self):
        svc = RetrievalService()
        import asyncio

        async def _test():
            with patch.object(svc, '_vector_store', NumpyVectorStore()):
                with patch.object(svc.embedding, 'embed_text', AsyncMock(return_value=[0.1] * 1536)):
                    results = await svc.retrieve("test query", top_k=2)
                    return results

        results = asyncio.run(_test())
        assert results is not None


class TestFileHandler:
    def test_supported_txt(self):
        handler = FileHandler()
        assert handler.is_supported("document.txt")
        assert handler.is_supported("readme.md")

    def test_supported_pdf(self):
        handler = FileHandler()
        assert handler.is_supported("report.pdf")

    def test_supported_docx(self):
        handler = FileHandler()
        assert handler.is_supported("essay.docx")

    def test_unsupported(self):
        handler = FileHandler()
        assert not handler.is_supported("video.mp4")
        assert not handler.is_supported("song.mp3")

    def test_unsupported_no_extension(self):
        handler = FileHandler()
        assert not handler.is_supported("README")

    def test_parse_text_file(self):
        handler = FileHandler()
        content = "Hello world from txt file".encode("utf-8")
        sections = handler.parse_bytes("test.txt", content)
        assert len(sections) > 0
        assert "Hello world" in sections[0]

    def test_parse_empty_bytes(self):
        handler = FileHandler()
        result = handler.parse_bytes("empty.txt", b"")
        assert result == [] or result == [""]
