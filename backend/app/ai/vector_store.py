from uuid import uuid4
from app.config import settings
from app.ai.dense import get_embedding_model, batch_embed
from app.ai.sparse import text_to_sparse
from app.ai.chunking import chunking_file
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Filter as QdrantFilter,
    FieldCondition,
    MatchValue,
    PointStruct,
    SparseVectorParams,
    SparseIndexParams,
    Modifier,
)


collection_initialized = False
qdrant_client: QdrantClient | None = None


def get_qdrant_client(timeout: int = 300) -> QdrantClient:
    global qdrant_client
    if qdrant_client is None:
        qdrant_client = QdrantClient(url=f"http://{settings.qdrant_host}:{settings.qdrant_port}", timeout=timeout)
    return qdrant_client


def ensure_collection(client: QdrantClient):
    global collection_initialized
    if collection_initialized:
        return
    collections = {c.name for c in client.get_collections().collections}
    if settings.qdrant_collection not in collections:
        client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config={"size": 1024, "distance": "Cosine"},
            sparse_vectors_config={
                "bm25": SparseVectorParams(
                    index=SparseIndexParams(),
                    modifier=Modifier.IDF,
                )
            },
        )
    collection_initialized = True


def init_vector_store(timeout: int = 300) -> QdrantClient:
    client = get_qdrant_client(timeout=timeout)
    ensure_collection(client)
    return client


async def process_document(content: bytes, filename: str, tag: str, doc_id: int, chunk_size: int = 1000, chunk_overlap: int = 50):
    try:
        chunks = await chunking_file(tag=tag, file_path=filename, file_bytes=content, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    except Exception as e:
        raise

    texts = [c["text"] for c in chunks]
    metadatas = []
    for c in chunks:
        meta = c["metadata"]
        meta["id"] = doc_id
        metadatas.append(meta)

    try:
        client = init_vector_store()
        embed_model = get_embedding_model()
    except Exception as e:
        raise

    try:
        dense_vectors = await batch_embed(embed_model, texts)
        sparse_vectors = [text_to_sparse(t) for t in texts]
        points = [
            PointStruct(
                id=str(uuid4()),
                vector={"": dense_vectors[i], "bm25": sparse_vectors[i]},
                payload={"text": texts[i], **metadatas[i]},
            )
            for i in range(len(texts))
        ]
        client.upsert(collection_name=settings.qdrant_collection, points=points)
    except Exception as e:
        raise


def delete_document_vectors(doc_id: int):
    client = get_qdrant_client()
    try:
        qdrant_filter = QdrantFilter(
            must=[FieldCondition(key="id", match=MatchValue(value=doc_id))]
        )
        deleted = 0
        while True:
            points, offset = client.scroll(
                collection_name=settings.qdrant_collection,
                limit=100,
                with_payload=False,
                with_vectors=False,
                scroll_filter=qdrant_filter,
            )
            if not points:
                break
            point_ids = [p.id for p in points]
            client.delete(
                collection_name=settings.qdrant_collection,
                points_selector=point_ids,
            )
            deleted += len(point_ids)
            if offset is None:
                break
    except Exception:
        pass
