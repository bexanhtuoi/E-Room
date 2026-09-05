from __future__ import annotations

import pytest

from app.ai.chunking import chunking_file


class TestRAGChunking:
    @pytest.mark.asyncio
    async def test_chunking_markdown_text(self):
        md_content = """# Header 1
This is the introduction.

## Subheader 1.1
Detailed explanation of AI agent architecture.

## Subheader 1.2
Explanation of RAG vector search.
"""
        chunks = await chunking_file(
            tag="ai",
            file_path="test.md",
            file_bytes=md_content.encode("utf-8"),
            chunk_size=200,
            chunk_overlap=20,
        )

        assert isinstance(chunks, list)
        assert len(chunks) >= 1
        for chunk in chunks:
            assert "text" in chunk
            assert "metadata" in chunk
            assert chunk["metadata"]["tag"] == "ai"
            assert chunk["metadata"]["source"] == "test.md"
