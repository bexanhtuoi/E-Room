from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from sqlmodel import JSON, Column, Field, SQLModel

from app.model.common import TimestampedModel


class DocumentStatus(StrEnum):
    PENDING = "pending"
    INDEXING = "indexing"
    READY = "ready"
    FAILED = "failed"


class KnowledgeDocumentBase(SQLModel):
    tag_id: UUID = Field(foreign_key="tags.id", index=True)
    title: str
    description: str | None = None
    file_path: str | None = None
    minio_key: str = Field(unique=True, index=True)
    file_type: str
    file_size_bytes: int = 0
    chunk_count: int = 0
    status: DocumentStatus = DocumentStatus.PENDING
    uploaded_by: UUID | None = Field(default=None, foreign_key="users.id")


class KnowledgeDocument(TimestampedModel, KnowledgeDocumentBase, table=True):
    __tablename__ = "knowledge_documents"


class KnowledgeChunkBase(SQLModel):
    document_id: UUID = Field(foreign_key="knowledge_documents.id", index=True)
    tag_id: UUID = Field(foreign_key="tags.id", index=True)
    content: str
    chunk_index: int = Field(ge=0)
    embedding: list[float] = Field(default_factory=list, sa_column=Column(JSON))
    chunk_metadata: dict = Field(default_factory=dict, sa_column=Column(JSON))


class KnowledgeChunk(TimestampedModel, KnowledgeChunkBase, table=True):
    __tablename__ = "knowledge_chunks"
