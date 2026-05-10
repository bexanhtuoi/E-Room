from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from typing import Any, BinaryIO

import httpx

from app.config import settings
from app.log import get_logger

logger = get_logger(__name__)

SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".docx"}
QUESTION_KEYS = {"question", "q", "query"}
ANSWER_KEYS = {"answer", "a", "response"}


def extract_qa(item: dict[str, Any]) -> tuple[str, str] | None:
    q = next((item[k] for k in QUESTION_KEYS if k in item), None)
    a = next((item[k] for k in ANSWER_KEYS if k in item), None)

    if not q or not a:
        return None

    return str(q).strip(), str(a).strip()


def extract_source_from_url(url: str) -> str:
    from urllib.parse import urlparse

    path = urlparse(url).path if "://" in url else url
    name = os.path.basename(path)
    return os.path.splitext(name)[0]


async def read_file_from_url(url: str) -> bytes:
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.content


class FileHandler:

    def __init__(self) -> None:
        self._supported = SUPPORTED_EXTENSIONS

    def is_supported(self, filename: str) -> bool:
        ext = os.path.splitext(filename)[1].lower()
        return ext in self._supported

    def parse_bytes(self, filename: str, content: bytes) -> list[str]:
        ext = os.path.splitext(filename)[1].lower()

        if ext == ".txt":
            return [content.decode("utf-8", errors="ignore")]
        elif ext == ".md":
            return self._parse_markdown(content.decode("utf-8", errors="ignore"))
        elif ext == ".pdf":
            return self._parse_pdf(content)
        elif ext == ".docx":
            return self._parse_docx(content)

        return []

    def _parse_markdown(self, text: str) -> list[str]:
        import re

        sections = re.split(r"\n(?=#{1,4}\s)", text)
        return [s.strip() for s in sections if s.strip()]

    def _parse_pdf(self, content: bytes) -> list[str]:
        try:
            from PyPDF2 import PdfReader
            from io import BytesIO

            reader = PdfReader(BytesIO(content))
            pages: list[str] = []

            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                if text and text.strip():
                    pages.append(f"[Page {i+1}]\n{text.strip()}")

            return pages
        except ImportError:
            logger.warning("PyPDF2 not installed, skipping PDF parse")
            return [f"[PDF file: {len(content)} bytes - PyPDF2 required for extraction]"]
        except Exception as e:
            logger.warning("pdf_parse_failed", extra={"error": str(e)})
            return []

    def _parse_docx(self, content: bytes) -> list[str]:
        try:
            from docx import Document
            from io import BytesIO

            doc = Document(BytesIO(content))
            paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]

            return paragraphs if paragraphs else [f"[DOCX file: {len(content)} bytes - no paragraphs found]"]
        except ImportError:
            logger.warning("python-docx not installed, skipping DOCX parse")
            return [f"[DOCX file: {len(content)} bytes - python-docx required for extraction]"]
        except Exception as e:
            logger.warning("docx_parse_failed", extra={"error": str(e)})
            return []

    async def upload_to_minio(self, filename: str, content: bytes) -> str | None:
        try:
            from app.infrastructure.minio import MinioClient

            client = MinioClient()
            file_hash = hashlib.sha256(content).hexdigest()[:16]
            ext = os.path.splitext(filename)[1]
            object_name = f"rag-docs/{file_hash}{ext}"

            client.upload_bytes(object_name, content, len(content))
            return object_name
        except ImportError:
            logger.warning("MinioClient not available")
            return None
        except Exception as e:
            logger.warning("minio_upload_failed", extra={"error": str(e)})
            return None

    def compute_hash(self, content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()
