from __future__ import annotations

import logging
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

import numpy as np

from app.config import settings
from app.log import get_logger

logger = get_logger(__name__)


class BaseVectorStore(ABC):
    """Abstract interface for vector storage and similarity search."""

    @abstractmethod
    def store_embeddings(self, items: list[dict[str, Any]]) -> int:
        """Store multiple embedding entries.

        Each item should contain: chunk_id, document_id, text, embedding,
        and optionally metadata, tag_id, created_at.
        Returns the number of items stored.
        """
        ...

    @abstractmethod
    def similarity_search(
        self,
        query_vector: list[float],
        top_k: int = 5,
        tag_id: str | None = None,
        document_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return top_k most similar chunks via cosine distance.

        Returns list of dicts with: chunk_id, document_id, text, score, metadata.
        """
        ...

    @abstractmethod
    def delete_by_document(self, document_id: str) -> int:
        """Delete all chunks belonging to a document. Returns count deleted."""
        ...

    @abstractmethod
    def count(self) -> int:
        """Return total number of stored vectors."""
        ...


class NumpyVectorStore(BaseVectorStore):
    """In-memory vector store backed by numpy arrays.

    Used as the SQLite / development fallback when pgvector is unavailable.
    Stores vectors in a contiguous float32 array for fast cosine similarity.
    """

    def __init__(self) -> None:
        self._ids: list[str] = []
        self._document_ids: list[str] = []
        self._texts: list[str] = []
        self._metadatas: list[dict[str, Any]] = []
        self._tag_ids: list[str] = []
        self._vectors: np.ndarray | None = None
        self._dim: int | None = None
        self._created_ats: list[str] = []

    def _normalize(self, vec: np.ndarray) -> np.ndarray:
        norm = np.linalg.norm(vec)
        if norm == 0:
            return vec
        return vec / norm

    def store_embeddings(self, items: list[dict[str, Any]]) -> int:
        """Store embedding entries in the in-memory array."""
        if not items:
            return 0

        new_vectors: list[np.ndarray] = []
        for item in items:
            emb = item.get("embedding")
            if emb is None:
                continue
            vec = np.array(emb, dtype=np.float32)
            if self._dim is None:
                self._dim = len(vec)
            elif len(vec) != self._dim:
                logger.warning(
                    "embedding_dimension_mismatch",
                    extra={"expected": self._dim, "got": len(vec)},
                )
                continue

            chunk_id = str(item.get("chunk_id", uuid.uuid4()))
            self._ids.append(chunk_id)
            self._document_ids.append(str(item.get("document_id", "")))
            self._texts.append(str(item.get("text", "")))
            self._metadatas.append(item.get("metadata") or {})
            self._tag_ids.append(str(item.get("tag_id", "")))
            self._created_ats.append(
                item.get("created_at") or datetime.now(timezone.utc).isoformat()
            )
            new_vectors.append(self._normalize(vec))

        if new_vectors:
            if self._vectors is None:
                self._vectors = np.stack(new_vectors)
            else:
                stacked = np.stack(new_vectors)
                self._vectors = np.vstack([self._vectors, stacked])

        return len(new_vectors)

    def similarity_search(
        self,
        query_vector: list[float],
        top_k: int = 5,
        tag_id: str | None = None,
        document_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search for top_k most similar chunks by cosine similarity."""
        if self._vectors is None or len(self._vectors) == 0:
            return []

        q_vec = np.array(query_vector, dtype=np.float32)
        q_norm = np.linalg.norm(q_vec)
        if q_norm == 0:
            return []

        q_normalized = q_vec / q_norm
        scores = np.dot(self._vectors, q_normalized)

        scored_indices: list[tuple[int, float]] = []
        for i, score in enumerate(scores):
            if tag_id and self._tag_ids[i] and self._tag_ids[i] != tag_id:
                continue
            if document_id and self._document_ids[i] != document_id:
                continue
            scored_indices.append((i, float(score)))

        scored_indices.sort(key=lambda x: x[1], reverse=True)
        top = scored_indices[:top_k]

        return [
            {
                "chunk_id": self._ids[i],
                "document_id": self._document_ids[i],
                "text": self._texts[i],
                "score": round(score, 6),
                "metadata": self._metadatas[i],
                "tag_id": self._tag_ids[i],
                "created_at": self._created_ats[i],
            }
            for i, score in top
        ]

    def delete_by_document(self, document_id: str) -> int:
        """Remove all chunks for a document. Returns count removed."""
        if self._vectors is None:
            return 0

        keep_indices: list[int] = []
        removed = 0
        for i, did in enumerate(self._document_ids):
            if did == document_id:
                removed += 1
            else:
                keep_indices.append(i)

        if removed == 0:
            return 0

        if not keep_indices:
            self._ids.clear()
            self._document_ids.clear()
            self._texts.clear()
            self._metadatas.clear()
            self._tag_ids.clear()
            self._vectors = None
            self._dim = None
            self._created_ats.clear()
            return removed

        mask = np.array(keep_indices, dtype=np.intp)
        self._ids = [self._ids[i] for i in keep_indices]
        self._document_ids = [self._document_ids[i] for i in keep_indices]
        self._texts = [self._texts[i] for i in keep_indices]
        self._metadatas = [self._metadatas[i] for i in keep_indices]
        self._tag_ids = [self._tag_ids[i] for i in keep_indices]
        self._created_ats = [self._created_ats[i] for i in keep_indices]
        self._vectors = self._vectors[mask]

        return removed

    def count(self) -> int:
        return len(self._ids)


class PgVectorStore(BaseVectorStore):
    """Vector store backed by PostgreSQL with the pgvector extension.

    Uses SQLAlchemy Core for efficient batch operations and
    the cosine distance operator (<=>) for similarity search.
    """

    def __init__(self, database_url: str) -> None:
        try:
            from sqlalchemy import create_engine, text
            self._engine = create_engine(database_url, echo=False)
            self._ensure_extension()
        except ImportError:
            raise RuntimeError(
                "SQLAlchemy is required for PgVectorStore. Install with: pip install sqlalchemy"
            )
        except Exception as e:
            raise RuntimeError(f"Failed to connect to PostgreSQL: {e}")

    def _get_table_name(self) -> str:
        return "rag_embeddings"

    def _ensure_extension(self) -> None:
        from sqlalchemy import text
        with self._engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
            conn.commit()

        with self._engine.connect() as conn:
            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS {self._get_table_name()} (
                    chunk_id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    text TEXT NOT NULL,
                    embedding vector(1536),
                    metadata JSONB DEFAULT '{{}}',
                    tag_id TEXT DEFAULT '',
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """))
            conn.execute(text(f"""
                CREATE INDEX IF NOT EXISTS idx_rag_embeddings_document_id
                ON {self._get_table_name()} (document_id)
            """))
            conn.execute(text(f"""
                CREATE INDEX IF NOT EXISTS idx_rag_embeddings_tag_id
                ON {self._get_table_name()} (tag_id)
            """))
            conn.commit()

    def store_embeddings(self, items: list[dict[str, Any]]) -> int:
        """Store embedding entries using batch INSERT."""
        if not items:
            return 0

        from sqlalchemy import text
        import json

        rows: list[dict[str, Any]] = []
        for item in items:
            emb = item.get("embedding")
            if emb is None:
                continue
            rows.append({
                "chunk_id": str(item.get("chunk_id", uuid.uuid4())),
                "document_id": str(item.get("document_id", "")),
                "text": str(item.get("text", "")),
                "embedding": json.dumps(emb),
                "metadata": json.dumps(item.get("metadata") or {}),
                "tag_id": str(item.get("tag_id", "")),
                "created_at": item.get("created_at") or datetime.now(timezone.utc).isoformat(),
            })

        if not rows:
            return 0

        with self._engine.begin() as conn:
            for row in rows:
                conn.execute(
                    text(f"""
                        INSERT INTO {self._get_table_name()}
                            (chunk_id, document_id, text, embedding, metadata, tag_id, created_at)
                        VALUES
                            (:chunk_id, :document_id, :text, :embedding::vector, :metadata::jsonb, :tag_id, :created_at)
                        ON CONFLICT (chunk_id) DO UPDATE SET
                            embedding = EXCLUDED.embedding,
                            text = EXCLUDED.text,
                            metadata = EXCLUDED.metadata
                    """),
                    row,
                )

        return len(rows)

    def similarity_search(
        self,
        query_vector: list[float],
        top_k: int = 5,
        tag_id: str | None = None,
        document_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Cosine similarity search using pgvector <=> operator.

        1 - cosine_distance converts distance to similarity score.
        """
        from sqlalchemy import text
        import json

        vec_str = json.dumps(query_vector)

        conditions = []
        params: dict[str, Any] = {"vec": vec_str, "top_k": top_k}

        if tag_id and tag_id.strip():
            conditions.append("tag_id = :tag_id")
            params["tag_id"] = tag_id
        if document_id and document_id.strip():
            conditions.append("document_id = :doc_id")
            params["doc_id"] = document_id

        where_clause = ""
        if conditions:
            where_clause = "AND " + " AND ".join(conditions)

        query = f"""
            SELECT
                chunk_id,
                document_id,
                text,
                1 - (embedding <=> :vec::vector) AS score,
                metadata,
                tag_id,
                created_at
            FROM {self._get_table_name()}
            WHERE embedding IS NOT NULL
            {where_clause}
            ORDER BY embedding <=> :vec::vector
            LIMIT :top_k
        """

        with self._engine.connect() as conn:
            result = conn.execute(text(query), params)
            rows = result.fetchall()

        return [
            {
                "chunk_id": row[0],
                "document_id": row[1],
                "text": row[2],
                "score": round(float(row[3]), 6),
                "metadata": row[4] if isinstance(row[4], dict) else json.loads(row[4] or "{}"),
                "tag_id": row[5] or "",
                "created_at": row[6].isoformat() if row[6] else "",
            }
            for row in rows
        ]

    def delete_by_document(self, document_id: str) -> int:
        """Delete all chunks belonging to a document."""
        from sqlalchemy import text

        with self._engine.begin() as conn:
            result = conn.execute(
                text(f"DELETE FROM {self._get_table_name()} WHERE document_id = :doc_id"),
                {"doc_id": document_id},
            )
            return result.rowcount

    def count(self) -> int:
        from sqlalchemy import text
        with self._engine.connect() as conn:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {self._get_table_name()}"))
            return result.scalar_one()


class TiDBVectorStore(BaseVectorStore):
    """Vector store backed by TiDB Cloud with native VECTOR type.

    TiDB 8.4+ supports VECTOR(FLOAT32, dim) column type and
    VEC_COSINE_DISTANCE function for cosine similarity search.
    Uses mysql+pymysql connection with SSL (TiDB Cloud requires TLS).

    Replaces PgVectorStore (PostgreSQL-only) for TiDB deployments.
    Nomic embeddings produce 768-dimensional vectors (default dim).
    """

    def __init__(self, database_url: str, dim: int = 768) -> None:
        try:
            from sqlalchemy import create_engine, text
        except ImportError:
            raise RuntimeError("SQLAlchemy and pymysql are required for TiDBVectorStore.")
        self._engine = create_engine(
            database_url,
            echo=False,
            connect_args={"ssl": {"ssl_mode": "PREFERRED"}},
        )
        self._dim = dim
        self._ensure_table()

    def _get_table_name(self) -> str:
        return "rag_embeddings"

    def _ensure_table(self) -> None:
        from sqlalchemy import text
        with self._engine.connect() as conn:
            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS {self._get_table_name()} (
                    chunk_id VARCHAR(36) PRIMARY KEY,
                    document_id VARCHAR(36) NOT NULL,
                    text TEXT NOT NULL,
                    embedding VECTOR(FLOAT32, {self._dim}),
                    metadata JSON DEFAULT ('{{}}'),
                    tag_id VARCHAR(36) DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()

    def store_embeddings(self, items: list[dict[str, Any]]) -> int:
        if not items:
            return 0

        from sqlalchemy import text
        import json

        rows: list[dict[str, Any]] = []
        for item in items:
            emb = item.get("embedding")
            if emb is None:
                continue
            rows.append({
                "chunk_id": str(item.get("chunk_id", str(uuid.uuid4()))),
                "document_id": str(item.get("document_id", "")),
                "text": str(item.get("text", "")),
                "embedding": json.dumps(emb),
                "metadata": json.dumps(item.get("metadata") or {}),
                "tag_id": str(item.get("tag_id", "")),
                "created_at": item.get("created_at") or datetime.now(timezone.utc).isoformat(),
            })

        if not rows:
            return 0

        with self._engine.begin() as conn:
            for row in rows:
                conn.execute(
                    text(f"""
                        INSERT INTO {self._get_table_name()}
                            (chunk_id, document_id, text, embedding, metadata, tag_id, created_at)
                        VALUES
                            (:chunk_id, :document_id, :text, :embedding, :metadata, :tag_id, :created_at)
                        ON DUPLICATE KEY UPDATE
                            embedding = VALUES(embedding),
                            text = VALUES(text),
                            metadata = VALUES(metadata)
                    """),
                    row,
                )

        return len(rows)

    def similarity_search(
        self,
        query_vector: list[float],
        top_k: int = 5,
        tag_id: str | None = None,
        document_id: str | None = None,
    ) -> list[dict[str, Any]]:
        from sqlalchemy import text
        import json

        vec_str = json.dumps(query_vector)
        conditions: list[str] = []
        params: dict[str, Any] = {"vec": vec_str, "top_k": top_k}

        if tag_id and tag_id.strip():
            conditions.append("tag_id = :tag_id")
            params["tag_id"] = tag_id
        if document_id and document_id.strip():
            conditions.append("document_id = :doc_id")
            params["doc_id"] = document_id

        where_clause = ""
        if conditions:
            where_clause = "AND " + " AND ".join(conditions)

        query = f"""
            SELECT chunk_id, document_id, text,
                   1 - VEC_COSINE_DISTANCE(embedding, :vec) AS score,
                   metadata, tag_id, created_at
            FROM {self._get_table_name()}
            WHERE embedding IS NOT NULL
            {where_clause}
            ORDER BY VEC_COSINE_DISTANCE(embedding, :vec)
            LIMIT :top_k
        """

        with self._engine.connect() as conn:
            result = conn.execute(text(query), params)
            rows = result.fetchall()

        return [
            {
                "chunk_id": row[0],
                "document_id": row[1],
                "text": row[2],
                "score": round(float(row[3]), 6),
                "metadata": row[4] if isinstance(row[4], dict) else json.loads(row[4] or "{}"),
                "tag_id": row[5] or "",
                "created_at": row[6].isoformat() if row[6] else "",
            }
            for row in rows
        ]

    def delete_by_document(self, document_id: str) -> int:
        from sqlalchemy import text
        with self._engine.begin() as conn:
            result = conn.execute(
                text(f"DELETE FROM {self._get_table_name()} WHERE document_id = :doc_id"),
                {"doc_id": document_id},
            )
            return result.rowcount

    def count(self) -> int:
        from sqlalchemy import text
        with self._engine.connect() as conn:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {self._get_table_name()}"))
            return result.scalar_one()


def _is_tidb(url: str) -> bool:
    """Check if database URL targets TiDB/MySQL."""
    return url.startswith("mysql+pymysql://") or url.startswith("mysql://")


def _is_postgres(url: str) -> bool:
    """Check if database URL targets PostgreSQL."""
    return url.startswith("postgresql://") or url.startswith("postgres://")


def _is_pgvector_available() -> bool:
    """Check if the pgvector Python package and SQLAlchemy are importable."""
    try:
        import importlib
        importlib.import_module("sqlalchemy")
        return True
    except ImportError:
        return False


_vector_store: BaseVectorStore | None = None


def get_vector_store() -> BaseVectorStore:
    """Get or create the singleton vector store instance.

    Uses pgvector-backed store when DATABASE_URL targets PostgreSQL,
    otherwise falls back to an in-memory numpy store.
    """
    global _vector_store
    if _vector_store is not None:
        return _vector_store

    db_url = settings.database_url_sync or settings.database_url

    if _is_postgres(db_url) and _is_pgvector_available():
        try:
            _vector_store = PgVectorStore(db_url)
            logger.info("vector_store_pgvector", extra={"url": db_url[:40]})
            return _vector_store
        except Exception as e:
            logger.warning("pgvector_init_failed_fallback_numpy", extra={"error": str(e)})

    if _is_tidb(db_url):
        try:
            _vector_store = TiDBVectorStore(db_url)
            logger.info("vector_store_tidb")
            return _vector_store
        except Exception as e:
            logger.warning("tidb_vector_init_failed", extra={"error": str(e)})

    logger.info("vector_store_numpy", extra={"reason": "sqlite_dev_mode"})
    _vector_store = NumpyVectorStore()
    return _vector_store


def reset_vector_store() -> None:
    """Reset the singleton (useful for testing)."""
    global _vector_store
    _vector_store = None


def store_embeddings(items: list[dict[str, Any]]) -> int:
    """Store multiple embedding entries in the vector store.

    Each item should contain: chunk_id, document_id, text, embedding,
    and optionally metadata, tag_id.

    Args:
        items: List of dicts with embedding data.

    Returns:
        Number of items stored.
    """
    return get_vector_store().store_embeddings(items)


def similarity_search(
    query_vector: list[float],
    top_k: int = 5,
    tag_id: str | None = None,
    document_id: str | None = None,
) -> list[dict[str, Any]]:
    """Find the top_k most similar chunks by cosine distance.

    Args:
        query_vector: The embedding vector to compare against.
        top_k: Number of results to return.
        tag_id: Optional filter by tag.
        document_id: Optional filter by document.

    Returns:
        List of dicts with chunk_id, document_id, text, score, metadata.
    """
    return get_vector_store().similarity_search(
        query_vector=query_vector,
        top_k=top_k,
        tag_id=tag_id,
        document_id=document_id,
    )


def delete_by_document(document_id: str) -> int:
    """Delete all embedding chunks belonging to a document.

    Args:
        document_id: The document whose chunks should be removed.

    Returns:
        Number of chunks deleted.
    """
    return get_vector_store().delete_by_document(document_id)


def vector_store_count() -> int:
    """Return the total number of stored vectors."""
    return get_vector_store().count()


VectorStore = NumpyVectorStore
