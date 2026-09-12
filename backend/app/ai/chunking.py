import os
import re
import tempfile
from typing import List

from langchain_text_splitters import MarkdownHeaderTextSplitter

from app.utils.file import (
    apply_noise_filter,
    extract_pdf_text,
    extract_source_from_url,
    read_file_from_url,
)


def normalize_split_text(text: str) -> str:
    text = re.sub(r"\n\n+", "\x00", text)
    text = re.sub(r"(\w+)-\n(\w+)", r"\1\2", text)
    text = text.replace("\n", " ")
    text = text.replace("\x00", "\n")
    text = re.sub(r"  +", " ", text)
    return text.strip()


def split_sentences(text: str) -> list[str]:
    sents = re.split(r"(?<=[.?!])\s+", text)
    return [s.strip() for s in sents if s.strip()]


def split_long_sentence(sent: str, min_size: int) -> list[str]:
    if len(sent) <= min_size:
        return [sent]

    idx = sent.rfind(",")
    if idx > 0:
        left = sent[:idx].strip()
        right = sent[idx + 1:].strip()
        if left and right:
            return split_long_sentence(left, min_size) + split_long_sentence(right, min_size)

    words = sent.split()
    if len(words) >= 2:
        mid = len(words) // 2
        left = " ".join(words[:mid]).strip()
        right = " ".join(words[mid:]).strip()
        if left and right:
            return split_long_sentence(left, min_size) + split_long_sentence(right, min_size)

    return [sent]


def group_sentences(pieces: list[str], min_size: int, max_size: int, overlap_chars: int) -> list[str]:
    chunks = []
    current = ""

    for piece in pieces:
        if current and len(current) + 1 + len(piece) > max_size and len(current) >= min_size:
            chunks.append(current)
            if overlap_chars > 0 and len(current) > overlap_chars:
                current = current[-overlap_chars:]
            else:
                current = ""

        if current:
            current += " "
        current += piece

    if current.strip():
        chunks.append(current)

    return chunks


def split_to_chunks(text: str, chunk_size: int = 600, chunk_overlap: int = 50) -> List[str]:
    text = normalize_split_text(text)
    if not text:
        return []

    pieces = []
    for sent in split_sentences(text):
        pieces.extend(split_long_sentence(sent, chunk_size))

    return [
        clean
        for chunk_text in group_sentences(pieces, chunk_size, chunk_size * 2, chunk_overlap)
        for clean in [re.sub(r"[ \t]+", " ", chunk_text).strip()]
        if clean
    ]


def chunking_pdf(
    file_path: str,
    tag: str,
    source: str,
    chunk_size: int = 600,
    chunk_overlap: int = 50,
) -> list[dict]:
    pages = extract_pdf_text(file_path)
    if not pages:
        return []

    documents = []
    chunk_counter = 0
    for page in pages:
        text = apply_noise_filter(page["text"])
        if not text.strip():
            continue

        for clean in split_to_chunks(text, chunk_size, chunk_overlap):
            chunk_counter += 1
            documents.append({
                "text": clean,
                "metadata": {
                    "source": source,
                    "location": f"Page {page['page']}",
                    "chunk_index": chunk_counter,
                    "tag": tag,
                    "type": "pdf",
                },
            })

    return documents


def chunking_md(
    file_bytes: bytes,
    tag: str,
    source: str,
    chunk_size: int = 600,
    chunk_overlap: int = 50,
) -> list[dict]:
    text = file_bytes.decode("utf-8", errors="ignore")
    if not text.strip():
        return []

    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[
            ("#", "h1"),
            ("##", "h2"),
            ("###", "h3"),
            ("####", "h4"),
        ]
    )

    md_docs = header_splitter.split_text(text)

    documents = []
    chunk_counter = 0
    for doc in md_docs:
        headers = doc.metadata
        location_parts = [
            headers.get("h1"),
            headers.get("h2"),
            headers.get("h3"),
            headers.get("h4"),
        ]
        location = " > ".join([h for h in location_parts if h])

        for clean in split_to_chunks(doc.page_content.strip(), chunk_size, chunk_overlap):
            chunk_counter += 1
            documents.append({
                "text": clean,
                "metadata": {
                    "source": source,
                    "location": location or "ROOT",
                    "chunk_index": chunk_counter,
                    "tag": tag,
                    "type": "md",
                },
            })

    return documents



async def chunking_file(
    tag: str,
    file_path: str = "./README.md",
    file_bytes: bytes | None = None,
    chunk_size: int = 600,
    chunk_overlap: int = 50,
) -> list[dict]:
    if file_bytes is None:
        file_bytes = await read_file_from_url(file_path)
    source = extract_source_from_url(file_path)

    if file_path.endswith(".pdf"):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
            f.write(file_bytes)
            tmp = f.name
        try:
            return chunking_pdf(tmp, tag, source, chunk_size, chunk_overlap)
        finally:
            os.unlink(tmp)

    elif file_path.endswith(".md"):
        return chunking_md(file_bytes, tag, source, chunk_size, chunk_overlap)

    else:
        raise ValueError(f"Unsupported file type: {file_path}")
