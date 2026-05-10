from __future__ import annotations

from celery import shared_task
from sqlmodel import Session

from app.database import engine
from app.log import get_logger
from app.model.document import KnowledgeDocument, DocumentStatus

logger = get_logger(__name__)


@shared_task(name="eroom.load_room_knowledge", bind=True, max_retries=3, default_retry_delay=10)
def load_room_knowledge(self, document_id: int) -> dict:
    try:
        with Session(engine) as session:
            doc = session.get(KnowledgeDocument, document_id)
            if not doc:
                return {"status": "error", "message": f"Document {document_id} not found"}

            doc.status = DocumentStatus.INDEXING
            session.add(doc)
            session.commit()

            from app.rag.chunking import TextChunker
            from app.rag.embedding import EmbeddingService
            from app.rag.vector_store import VectorStore
            import asyncio

            text = ""
            if doc.file_path:
                try:
                    with open(doc.file_path, "r", encoding="utf-8") as f:
                        text = f.read()
                except Exception:
                    pass

            if not text:
                doc.status = DocumentStatus.READY
                doc.chunk_count = 0
                session.add(doc)
                session.commit()
                return {"status": "completed", "chunks": 0}

            chunker = TextChunker(chunk_size=512, chunk_overlap=64)
            chunks = chunker.chunk_text(text)

            if not chunks:
                doc.status = DocumentStatus.READY
                doc.chunk_count = 0
                session.add(doc)
                session.commit()
                return {"status": "completed", "chunks": 0}

            embed_service = EmbeddingService()
            vectors = asyncio.run(embed_service.embed_batch(chunks))

            vs = VectorStore()
            items = [
                (
                    f"doc_{document_id}_chunk_{i}",
                    vec,
                    {
                        "text": chunk,
                        "source": doc.file_path or "",
                        "tag": str(doc.tag_id) if doc.tag_id else "",
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                    },
                )
                for i, (chunk, vec) in enumerate(zip(chunks, vectors))
            ]
            vs.add_batch(items)

            doc.status = DocumentStatus.READY
            doc.chunk_count = len(chunks)
            session.add(doc)
            session.commit()

            logger.info("rag_load_done", extra={"doc_id": document_id, "chunks": len(chunks)})
            return {"status": "completed", "chunks": len(chunks)}

    except Exception as e:
        logger.error("rag_load_failed", exc_info=True)
        try:
            with Session(engine) as session:
                doc = session.get(KnowledgeDocument, document_id)
                if doc:
                    doc.status = DocumentStatus.FAILED
                    session.add(doc)
                    session.commit()
        except Exception:
            pass
        raise self.retry(exc=e)
