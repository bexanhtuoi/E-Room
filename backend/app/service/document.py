from __future__ import annotations

from app.model import DocumentStatus, KnowledgeChunk, KnowledgeDocument
from app.service.base import BaseService


class DocumentService(BaseService[KnowledgeDocument]):
    def list_documents_by_tag(self, tag_id: str) -> list[KnowledgeDocument]:
        return [document for document in self.list_all() if document.tag_id == tag_id]

    def mark_ready(self, document_id: str, chunk_count: int) -> KnowledgeDocument | None:
        document = self.get_by_id(document_id)
        if document is None:
            return None
        document.status = DocumentStatus.READY
        document.chunk_count = chunk_count
        return self.save(document)


class KnowledgeChunkService(BaseService[KnowledgeChunk]):
    def list_chunks_by_tag(self, tag_id: str) -> list[KnowledgeChunk]:
        return [chunk for chunk in self.list_all() if chunk.tag_id == tag_id]
