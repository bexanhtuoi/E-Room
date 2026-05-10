from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import numpy as np
from langchain_community.vectorstores import TiDBVectorStore

from app.config import settings
from app.log import get_logger
from app.rag.embedding import get_embedding_model

logger = get_logger(__name__)

_tidb_vector_store: TiDBVectorStore | None = None


def init_vector_store() -> TiDBVectorStore:
    global _tidb_vector_store
    if _tidb_vector_store is not None:
        return _tidb_vector_store
    _tidb_vector_store = TiDBVectorStore(
        table_name="rag_embeddings",
        connection_string=settings.database_url,
        embedding_function=get_embedding_model(),
        engine_args={
            "pool_pre_ping": True,
            "pool_recycle": 300,
            "connect_args": {"ssl": {"ssl_mode": "PREFERRED"}},
        },
    )
    logger.info("tidb_vector_store_initialized")
    return _tidb_vector_store


def reset_vector_store() -> None:
    global _tidb_vector_store
    _tidb_vector_store = None


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
        self._store: TiDBVectorStore | NumpyVectorStore | None = None
        self._is_tidb = True

    def _get_store(self) -> TiDBVectorStore | NumpyVectorStore:
        if self._store is None:
            try:
                self._store = init_vector_store()
            except Exception as e:
                logger.warning("tidb_fallback_numpy", extra={"error": str(e)})
                self._store = NumpyVectorStore()
                self._is_tidb = False
        return self._store

    def add_batch(self, items: list[tuple[str, list[float], dict]]) -> list[str]:
        store = self._get_store()
        if isinstance(store, TiDBVectorStore):
            texts = [meta.get("text", "") for _, _, meta in items]
            metadatas = [
                {**meta, "chunk_id": cid}
                for cid, _, meta in items
            ]
            return store.add_texts(texts=texts, metadatas=metadatas)
        numpy_items = [
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
        if isinstance(store, TiDBVectorStore):
            filter_dict = {}
            if tag_id:
                filter_dict["tag_id"] = tag_id
            if document_id:
                filter_dict["document_id"] = document_id
            from langchain_core.runnables.config import run_in_executor
            import asyncio
            docs = asyncio.get_event_loop().run_until_complete(
                run_in_executor(
                    None,
                    store.similarity_search_with_score,
                    "dummy query",
                    top_k,
                    filter=filter_dict if filter_dict else None,
                )
            )
            results = []
            for doc, score in docs:
                results.append({
                    "chunk_id": doc.metadata.get("chunk_id", ""),
                    "text": doc.page_content,
                    "score": round(float(score), 6),
                    "metadata": doc.metadata,
                    "tag_id": doc.metadata.get("tag", ""),
                })
            return results
        return store.similarity_search(query_vector, top_k, tag_id, document_id)

    def delete_by_document(self, document_id: str) -> int:
        store = self._get_store()
        if isinstance(store, TiDBVectorStore):
            store.delete(filter={"document_id": document_id})
            return 1
        return store.delete_by_document(document_id)

    def count(self) -> int:
        store = self._get_store()
        return store.count()
