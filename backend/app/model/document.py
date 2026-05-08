from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from app.model.common import BaseEntity


class DocumentStatus(StrEnum):
    PENDING = "pending"
    INDEXING = "indexing"
    READY = "ready"
    FAILED = "failed"


class KnowledgeDocument(BaseEntity):
    tag_id: str
    title: str
    description: str | None = None
    file_path: str | None = None
    minio_key: str
    file_type: str
    file_size_bytes: int = Field(default=0, ge=0)
    chunk_count: int = Field(default=0, ge=0)
    status: DocumentStatus = DocumentStatus.PENDING
    uploaded_by: str | None = None


class KnowledgeChunk(BaseEntity):
    document_id: str
    tag_id: str
    content: str
    chunk_index: int = Field(ge=0)
    embedding: list[float] = Field(default_factory=list)
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
