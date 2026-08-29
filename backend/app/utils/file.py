import os
import re
from urllib.parse import urlparse

import httpx
import pymupdf

QUESTION_KEYS = {"question", "q", "query"}
ANSWER_KEYS = {"answer", "a", "response"}

NOISE_PATTERNS = [
    re.compile(r"<a\s+[^>]*></a>", re.IGNORECASE),
    re.compile(r"arXiv:\d+\.\d+v?\d*"),
    re.compile(r"^\d+\.\s*(?:\[\d+\]|\d+\s*$)", re.MULTILINE),
    re.compile(r"^\[\d+\]", re.MULTILINE),
]


def apply_noise_filter(text: str) -> str:
    for pattern in NOISE_PATTERNS:
        text = pattern.sub("", text)
    lines = text.split("\n")
    filtered = [l for l in lines if not re.match(r"^\s*\d+\s*$", l)]
    return "\n".join(filtered).strip()


def normalize_text(text: str) -> str:
    lines = text.split("\n")
    cleaned = []
    for l in lines:
        collapsed = re.sub(r"\s+", " ", l)
        if collapsed.strip():
            cleaned.append(collapsed)
        elif not collapsed:
            cleaned.append("")
    return "\n".join(cleaned)


def rebuild_text(raw: dict) -> str:
    blocks_text = []
    for block in raw.get("blocks", []):
        if block.get("type") != 0:
            continue
        lines_text = []
        for line in block.get("lines", []):
            chars = []
            for span in line.get("spans", []):
                font_size = span.get("size", 10)
                threshold = max(font_size * 0.12, 0.5)
                span_chars = span.get("chars", [])
                for i, ch_data in enumerate(span_chars):
                    ch = ch_data.get("c", "")
                    if ch == " ":
                        chars.append(" ")
                        continue
                    if i > 0:
                        prev_ch = span_chars[i - 1].get("c", "")
                        if prev_ch != " ":
                            prev_right = span_chars[i - 1]["bbox"][2]
                            curr_left = ch_data["bbox"][0]
                            if curr_left - prev_right > threshold:
                                chars.append(" ")
                    chars.append(ch)
            lines_text.append("".join(chars).strip())
        filtered = [l for l in lines_text if l]
        if filtered:
            blocks_text.append("\n".join(filtered))
    return "\n\n".join(blocks_text)


def extract_pdf_text(file_path: str) -> list[dict]:
    doc = pymupdf.open(file_path)
    pages = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = rebuild_text(page.get_text("rawdict"))
        if text.strip():
            pages.append({
                "text": text,
                "page": page_num + 1,
            })
    doc.close()
    return pages


def extract_qa(item: dict) -> tuple[str, str] | None:
    q = next((item[k] for k in QUESTION_KEYS if k in item), None)
    a = next((item[k] for k in ANSWER_KEYS if k in item), None)
    if not q or not a:
        return None
    return str(q).strip(), str(a).strip()


def extract_source_from_url(url: str) -> str:
    return os.path.basename(urlparse(url).path) or "unknown"


async def read_file_from_url(url: str) -> bytes:
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.content
