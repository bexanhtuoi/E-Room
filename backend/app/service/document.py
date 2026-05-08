from __future__ import annotations

from app.model import DocumentStatus, KnowledgeChunk, KnowledgeDocument
from app.service.base import CRUDRepository


class DocumentService:
    def __init__(self, session) -> None:
        self.session = session
        self.repo = CRUDRepository(KnowledgeDocument)

    def get_by_id(self, id):
        return self.session.get(self.repo._model, id)

    def list_all(self):
        return self.repo.get_many(self.session)

    def list_documents_by_tag(self, tag_id: str) -> list[KnowledgeDocument]:
        return [document for document in self.repo.get_many(self.session) if document.tag_id == tag_id]

    def mark_ready(self, document_id: str, chunk_count: int) -> KnowledgeDocument | None:
        document = self.get_by_id(document_id)
        if document is None:
            return None
        document.status = DocumentStatus.READY
        document.chunk_count = chunk_count
        self.session.add(document)
        self.session.commit()
        self.session.refresh(document)
        return document


class KnowledgeChunkService:
    def __init__(self, session) -> None:
        self.session = session
        self.repo = CRUDRepository(KnowledgeChunk)

    def list_all(self):
        return self.repo.get_many(self.session)

    def list_chunks_by_tag(self, tag_id: str) -> list[KnowledgeChunk]:
        return [chunk for chunk in self.repo.get_many(self.session) if chunk.tag_id == tag_id]
