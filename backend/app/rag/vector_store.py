from __future__ import annotations

import asyncio
import pickle
import uuid
from datetime import datetime, timezone
from typing import Any

import numpy as np
from langchain_core.documents import Document
from sqlalchemy import JSON, Column, LargeBinary, MetaData, String, Table, Text
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.orm import Session

from app.database import engine
from app.log import get_logger
from app.rag.embedding import EmbeddingService

logger = get_logger(__name__)

_rag_metadata = MetaData()

_rag_embeddings_table = Table(
    "rag_embeddings",
    _rag_metadata,
    Column("id", String(64), primary_key=True),
    Column("text", Text, nullable=False),
    Column("meta", JSON, nullable=False),
    Column("embedding", LargeBinary, nullable=False),
)

_tidb_raw_store: TiDBRawVectorStore | None = None


class TiDBRawVectorStore:
    def __init__(self) -> None:
        self._embed_service: EmbeddingService | None = None

    def _get_embed_service(self) -> EmbeddingService:
        if self._embed_service is None:
            self._embed_service = EmbeddingService()
        return self._embed_service

    def _get_session(self) -> Session:
        return Session(engine)

    def _ensure_table(self) -> None:
        _rag_metadata.create_all(engine, checkfirst=True)

    def add_texts(
        self,
        texts: list[str],
        metadatas: list[dict[str, Any]],
        embeddings: list[list[float]],
    ) -> list[str]:
        self._ensure_table()
        ids: list[str] = []
        with self._get_session() as session:
            for text, meta, emb in zip(texts, metadatas, embeddings):
                chunk_id = str(meta.get("chunk_id", str(uuid.uuid4())))
                ids.append(chunk_id)
                emb_bytes = pickle.dumps(np.array(emb, dtype=np.float32))
                stmt = mysql_insert(_rag_embeddings_table).values(
                    id=chunk_id, text=text, meta=meta, embedding=emb_bytes
                )
                stmt = stmt.on_duplicate_key_update(
                    text=stmt.inserted.text,
                    meta=stmt.inserted.meta,
                    embedding=stmt.inserted.embedding,
                )
                session.execute(stmt)
            session.commit()
        logger.info("tidb_raw_store_added", extra={"count": len(ids)})
        return ids

    def similarity_search(
        self,
        query_text: str,
        k: int = 10,
        filter: dict[str, Any] | None = None,
    ) -> list[Document]:
        embed_service = self._get_embed_service()
        query_vec = asyncio.run(embed_service.embed_query(query_text))
        return self.similarity_search_by_vector(query_vec, k, filter)

    def _load_all_rows(
        self, filter: dict[str, Any] | None
    ) -> list[tuple[str, str, dict[str, Any], np.ndarray]]:
        self._ensure_table()
        rows: list[tuple[str, str, dict[str, Any], np.ndarray]] = []
        with self._get_session() as session:
            result = session.execute(
                _rag_embeddings_table.select()
            )
            for row in result:
                row_meta: dict[str, Any] = row.meta or {}
                if filter:
                    matched = True
                    for kf, vf in filter.items():
                        if row_meta.get(kf) != vf:
                            matched = False
                            break
                    if not matched:
                        continue
                try:
                    vec = pickle.loads(row.embedding)
                except Exception:
                    continue
                rows.append((row.id, row.text, row_meta, vec))
        return rows

    def similarity_search_by_vector(
        self,
        query_vector: list[float],
        k: int = 10,
        filter: dict[str, Any] | None = None,
    ) -> list[Document]:
        qv = np.array(query_vector, dtype=np.float32)
        qv_norm = np.linalg.norm(qv)
        rows = self._load_all_rows(filter)

        scored: list[tuple[float, str, str, dict[str, Any]]] = []
        for row_id, text, meta, vec in rows:
            vec_norm = np.linalg.norm(vec)
            if qv_norm == 0 or vec_norm == 0:
                score = 0.0
            else:
                score = float(np.dot(qv, vec) / (qv_norm * vec_norm))
            scored.append((score, row_id, text, meta))

        scored.sort(key=lambda x: x[0], reverse=True)
        docs: list[Document] = []
        for score, _, text, meta in scored[:k]:
            docs.append(Document(page_content=text, metadata={**meta, "score": score}))
        return docs

    def similarity_search_with_score(
        self,
        query_text: str,
        k: int = 10,
        filter: dict[str, Any] | None = None,
    ) -> list[tuple[Document, float]]:
        docs = self.similarity_search(query_text, k, filter)
        return [(doc, float(doc.metadata.get("score", 0.0))) for doc in docs]

    def delete(self, filter: dict[str, Any]) -> bool:
        self._ensure_table()
        deleted_count = 0
        with self._get_session() as session:
            result = session.execute(
                _rag_embeddings_table.select()
            )
            for row in result:
                row_meta: dict[str, Any] = row.meta or {}
                matched = True
                for k, v in filter.items():
                    if row_meta.get(k) != v:
                        matched = False
                        break
                if matched:
                    session.execute(
                        _rag_embeddings_table.delete().where(
                            _rag_embeddings_table.c.id == row.id
                        )
                    )
                    deleted_count += 1
            session.commit()
        return deleted_count > 0

    def count(self) -> int:
        self._ensure_table()
        with self._get_session() as session:
            result = session.execute(
                _rag_embeddings_table.select()
            )
            return len(list(result))


class NumpyVectorStore:
    def __init__(self) -> None:
        self._vectors: dict[str, np.ndarray] = {}
        self._texts: dict[str, str] = {}
        self._docs: dict[str, dict[str, Any]] = {}
        self._dim: int | None = None

    def store_embeddings(self, items: list[dict[str, Any]]) -> int:
        count = 0
        for item in items:
            chunk_id = item.get("chunk_id", str(uuid.uuid4()))
            emb = item.get("embedding")
            if emb is None:
                continue
            arr = np.array(emb, dtype=np.float32)
            if self._dim is None:
                self._dim = len(arr)
            self._vectors[chunk_id] = arr
            self._texts[chunk_id] = str(item.get("text", ""))
            self._docs[chunk_id] = {
                "chunk_id": chunk_id,
                "document_id": str(item.get("document_id", "")),
                "text": str(item.get("text", "")),
                "metadata": item.get("metadata") or {},
                "tag_id": str(item.get("tag_id", "")),
                "created_at": item.get("created_at", datetime.now(timezone.utc).isoformat()),
            }
            count += 1
        return count

    def similarity_search(
        self,
        query_vector: list[float],
        top_k: int = 5,
        tag_id: str | None = None,
        document_id: str | None = None,
    ) -> list[dict[str, Any]]:
        if not self._vectors:
            return []
        qv = np.array(query_vector, dtype=np.float32)
        qv_norm = np.linalg.norm(qv)
        scored: list[tuple[float, str]] = []
        for cid, vec in self._vectors.items():
            if tag_id and self._docs[cid].get("tag_id") != tag_id:
                continue
            if document_id and self._docs[cid].get("document_id") != document_id:
                continue
            vec_norm = np.linalg.norm(vec)
            if qv_norm == 0 or vec_norm == 0:
                score = 0.0
            else:
                score = float(np.dot(qv, vec) / (qv_norm * vec_norm))
            scored.append((score, cid))
        scored.sort(key=lambda x: x[0], reverse=True)
        results = []
        for score, cid in scored[:top_k]:
            entry = {**self._docs[cid], "score": round(score, 6)}
            results.append(entry)
        return results

    def delete_by_document(self, document_id: str) -> int:
        to_delete = [
            cid for cid, doc in self._docs.items()
            if doc.get("document_id") == document_id
        ]
        for cid in to_delete:
            self._vectors.pop(cid, None)
            self._texts.pop(cid, None)
            self._docs.pop(cid, None)
        return len(to_delete)

    def count(self) -> int:
        return len(self._vectors)


class VectorStore:
    def __init__(self) -> None:
        self._store: TiDBRawVectorStore | NumpyVectorStore | None = None
        self._is_tidb: bool = True

    def _get_store(self) -> TiDBRawVectorStore | NumpyVectorStore:
        if self._store is not None:
            return self._store
        try:
            self._store = TiDBRawVectorStore()
            self._store.count()
        except Exception as e:
            logger.warning("tidb_fallback_numpy", extra={"error": str(e)})
            self._store = NumpyVectorStore()
            self._is_tidb = False
        return self._store

    def add_batch(self, items: list[tuple[str, list[float], dict[str, Any]]]) -> list[str]:
        store = self._get_store()
        if isinstance(store, TiDBRawVectorStore):
            embeddings = [vec for _, vec, _ in items]
            texts = [meta.get("text", "") for _, _, meta in items]
            metadatas = [
                {**meta, "chunk_id": cid}
                for cid, _, meta in items
            ]
            return store.add_texts(texts=texts, metadatas=metadatas, embeddings=embeddings)
        numpy_items: list[dict[str, Any]] = [
            {
                "chunk_id": cid,
                "document_id": meta.get("source", "unknown"),
                "text": meta.get("text", ""),
                "embedding": vec,
                "metadata": meta,
                "tag_id": meta.get("tag", ""),
            }
            for cid, vec, meta in items
        ]
        store.store_embeddings(numpy_items)
        return [cid for cid, _, _ in items]

    def similarity_search(
        self,
        query_vector: list[float],
        top_k: int = 5,
        tag_id: str | None = None,
        document_id: str | None = None,
    ) -> list[dict[str, Any]]:
        store = self._get_store()
        if isinstance(store, TiDBRawVectorStore):
            filter_dict: dict[str, Any] = {}
            if tag_id:
                filter_dict["tag_id"] = tag_id
            if document_id:
                filter_dict["document_id"] = document_id
            docs = store.similarity_search_by_vector(
                query_vector,
                top_k,
                filter_dict if filter_dict else None,
            )
            results: list[dict[str, Any]] = []
            for doc in docs:
                results.append({
                    "chunk_id": doc.metadata.get("chunk_id", ""),
                    "text": doc.page_content,
                    "score": round(float(doc.metadata.get("score", 0)), 6),
                    "metadata": doc.metadata,
                    "tag_id": doc.metadata.get("tag", ""),
                })
            return results
        return store.similarity_search(query_vector, top_k, tag_id, document_id)

    def delete_by_document(self, document_id: str) -> int:
        store = self._get_store()
        if isinstance(store, TiDBRawVectorStore):
            deleted = store.delete({"document_id": document_id})
            return 1 if deleted else 0
        return store.delete_by_document(document_id)

    def count(self) -> int:
        store = self._get_store()
        return store.count()


def init_vector_store() -> TiDBRawVectorStore:
    global _tidb_raw_store
    if _tidb_raw_store is not None:
        return _tidb_raw_store
    _tidb_raw_store = TiDBRawVectorStore()
    logger.info("tidb_vector_store_initialized")
    return _tidb_raw_store


def reset_vector_store() -> None:
    global _tidb_raw_store
    _tidb_raw_store = None
