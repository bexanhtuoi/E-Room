from __future__ import annotations

import asyncio

from celery import shared_task
from sqlmodel import Session

from app.database import engine
from app.log import get_logger
from app.model.document import KnowledgeDocument, DocumentStatus

logger = get_logger(__name__)


def _read_doc_text(doc: KnowledgeDocument) -> str:
    if not doc.file_path:
        return ""
    try:
        with open(doc.file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


def _mark_doc_status(session: Session, doc: KnowledgeDocument, status: DocumentStatus, chunk_count: int = 0) -> None:
    doc.status = status
    doc.chunk_count = chunk_count
    session.add(doc)
    session.commit()


def _chunk_and_embed(text: str) -> list[tuple[str, list[float]]]:
    from app.rag.chunking import TextChunker
    from app.rag.embedding import EmbeddingService

    chunker = TextChunker(chunk_size=512, chunk_overlap=64)
    chunks = chunker.chunk_text(text)

    if not chunks:
        return []

    embed_service = EmbeddingService()
    vectors = asyncio.run(embed_service.embed_batch(chunks))
    return list(zip(chunks, vectors))


def _build_vector_items(doc_id: int, pairs: list[tuple[str, list[float]]], source: str, tag: str) -> list:
    return [
        (
            f"doc_{doc_id}_chunk_{i}",
            vec,
            {
                "text": chunk,
                "source": source,
                "tag": tag,
                "chunk_index": i,
                "total_chunks": len(pairs),
            },
        )
        for i, (chunk, vec) in enumerate(pairs)
    ]


@shared_task(name="eroom.load_room_knowledge", bind=True, max_retries=3, default_retry_delay=10)
def load_room_knowledge(self, document_id: int) -> dict:
    try:
        with Session(engine) as session:
            doc = session.get(KnowledgeDocument, document_id)
            if not doc:
                return {"status": "error", "message": f"Document {document_id} not found"}

            _mark_doc_status(session, doc, DocumentStatus.INDEXING)

            text = _read_doc_text(doc)
            if not text:
                _mark_doc_status(session, doc, DocumentStatus.READY)
                return {"status": "completed", "chunks": 0}

            pairs = _chunk_and_embed(text)
            if not pairs:
                _mark_doc_status(session, doc, DocumentStatus.READY)
                return {"status": "completed", "chunks": 0}

            tag = str(doc.tag_id) if doc.tag_id else ""
            items = _build_vector_items(document_id, pairs, doc.file_path or "", tag)

            from app.rag.vector_store import VectorStore
            vs = VectorStore()
            vs.add_batch(items)

            _mark_doc_status(session, doc, DocumentStatus.READY, len(pairs))

            logger.info("rag_load_done", extra={"doc_id": document_id, "chunks": len(pairs)})
            return {"status": "completed", "chunks": len(pairs)}

    except Exception as e:
        logger.error("rag_load_failed", exc_info=True)
        try:
            with Session(engine) as session:
                doc = session.get(KnowledgeDocument, document_id)
                if doc:
                    _mark_doc_status(session, doc, DocumentStatus.FAILED)
        except Exception:
            pass
        raise self.retry(exc=e)
