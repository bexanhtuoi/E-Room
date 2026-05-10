from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from langchain_text_splitters import RecursiveCharacterTextSplitter


@dataclass
class ChunkResult:
    text: str
    chunk_index: int
    start_char: int
    end_char: int


_HEADING_PATTERN = re.compile(r"^(#{1,6}\s+.+)$", re.MULTILINE)


class TextChunker:
    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 64,
        separators: list | None = None,
    ) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._separators = separators
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=separators or [
                "\n\n", "\n", ". ", "? ", "! ", "。", "？", "！", " ", "",
            ],
        )

    def chunk_text(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []
        return self._splitter.split_text(text.strip())

    def chunk_documents(self, documents: list[dict[str, Any]]) -> list[ChunkResult]:
        results: list[ChunkResult] = []
        for doc in documents:
            text = doc.get("text", "")
            chunks = self.chunk_text(text)
            for i, chunk in enumerate(chunks):
                start = text.find(chunk)
                if start == -1:
                    start = 0
                results.append(ChunkResult(
                    text=chunk,
                    chunk_index=i,
                    start_char=start,
                    end_char=start + len(chunk),
                ))
        return results


def split_text(
    text: str,
    chunk_size: int = 512,
    chunk_overlap: int = 64,
    separators: list | None = None,
) -> list[str]:
    chunker = TextChunker(chunk_size, chunk_overlap, separators)
    return chunker.chunk_text(text)


def chunk_documents(
    documents: list[dict[str, Any]],
    chunk_size: int = 512,
    chunk_overlap: int = 64,
) -> list[ChunkResult]:
    chunker = TextChunker(chunk_size, chunk_overlap)
    return chunker.chunk_documents(documents)
