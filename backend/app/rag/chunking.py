from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass
class ChunkResult:
    """A text chunk with position metadata."""

    text: str
    chunk_index: int
    start_char: int
    end_char: int


_PARAGRAPH_SEPARATOR = "\n\n"
_LINE_SEPARATOR = "\n"
_SENTENCE_PATTERN = re.compile(r"(?<=[.!?。！？])\s+")
_WORD_SEPARATOR = " "

_HEADING_PATTERN = re.compile(r"^(#{1,6}\s+.+)$", re.MULTILINE)


def _get_separator_len(sep):
    """Return the length of a separator, handling regex patterns."""
    if isinstance(sep, re.Pattern):
        return 1
    return len(sep)


def _recursive_split(
    text: str,
    separators: list,
    chunk_size: int,
    chunk_overlap: int,
) -> list[str]:
    """Recursively split text using a hierarchy of separators.

    Tries each separator in order. If a chunk is still too large after
    splitting with the finest separator, falls back to character-level
    splitting with overlap.
    """
    if not separators:
        return _character_split(text, chunk_size, chunk_overlap)

    separator = separators[0]
    remaining = separators[1:]
    sep_str = " " if isinstance(separator, re.Pattern) else separator
    sep_len = _get_separator_len(separator)

    if isinstance(separator, re.Pattern):
        splits = separator.split(text)
        merged: list[str] = []
        buf = ""
        for part in splits:
            candidate = buf + sep_str + part if buf else part
            if len(candidate) <= chunk_size * 2:
                buf = candidate
            else:
                if buf:
                    merged.append(buf)
                buf = part
        if buf:
            merged.append(buf)
    else:
        merged = text.split(separator)

    chunks: list[str] = []
    current_chunk = ""
    for piece in merged:
        piece = piece.strip()
        if not piece:
            continue
        if not current_chunk:
            current_chunk = piece
        elif len(current_chunk) + sep_len + len(piece) <= chunk_size:
            current_chunk += sep_str + piece
        else:
            if len(current_chunk) > chunk_size:
                chunks.extend(_recursive_split(current_chunk, remaining, chunk_size, chunk_overlap))
            else:
                chunks.append(current_chunk)
            current_chunk = piece

    if current_chunk:
        if len(current_chunk) > chunk_size:
            chunks.extend(_recursive_split(current_chunk, remaining, chunk_size, chunk_overlap))
        else:
            chunks.append(current_chunk)

    return chunks


def _character_split(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """Split text into overlapping character-level chunks (last-resort fallback)."""
    if len(text) <= chunk_size:
        return [text] if text.strip() else []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += chunk_size - chunk_overlap
        if start >= len(text):
            break
    return chunks


def split_text(
    text: str,
    chunk_size: int = 512,
    chunk_overlap: int = 64,
    separators: list | None = None,
) -> list[str]:
    """Split text into chunks using a hierarchy of separators.

    Args:
        text: The text to split.
        chunk_size: Maximum size of each chunk in characters.
        chunk_overlap: Number of characters to overlap between chunks.
        separators: Optional custom separator hierarchy.
            Defaults to paragraph, line, sentence, then word.

    Returns:
        A list of text chunks. Empty string returns empty list.
    """
    if not text or not text.strip():
        return []

    if separators is None:
        separators = [
            _PARAGRAPH_SEPARATOR,
            _LINE_SEPARATOR,
            _SENTENCE_PATTERN,
            _WORD_SEPARATOR,
        ]

    return _recursive_split(text.strip(), separators, chunk_size, chunk_overlap)


def chunk_documents(
    documents: list[dict[str, Any]],
    chunk_size: int = 512,
    chunk_overlap: int = 64,
) -> list[ChunkResult]:
    """Chunk multiple documents and return structured results.

    Args:
        documents: List of document dicts with "text" and "metadata" keys.
        chunk_size: Maximum chunk size.
        chunk_overlap: Overlap between chunks.

    Returns:
        A flat list of ChunkResult objects across all documents.
    """
    results: list[ChunkResult] = []
    for doc in documents:
        text = doc.get("text", "")
        metadata = doc.get("metadata", {})
        chunks = split_text(text, chunk_size, chunk_overlap)
        for i, chunk in enumerate(chunks):
            start = text.find(chunk) if i == 0 else text.find(chunk, results[-1].end_char if results else 0)
            if start == -1:
                start = 0
            end = start + len(chunk)
            results.append(ChunkResult(
                text=chunk,
                chunk_index=i,
                start_char=start,
                end_char=end,
            ))
    return results


class TextChunker:
    """Configurable text chunker with recursive splitting."""

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 64,
        separators: list | None = None,
    ) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._separators = separators

    def chunk_text(self, text: str) -> list[str]:
        """Split text into chunks."""
        return split_text(text, self.chunk_size, self.chunk_overlap, self._separators)

    def chunk_documents(self, documents: list[dict[str, Any]]) -> list[ChunkResult]:
        """Chunk multiple documents."""
        return chunk_documents(documents, self.chunk_size, self.chunk_overlap)
