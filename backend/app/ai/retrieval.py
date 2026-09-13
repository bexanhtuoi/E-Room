import asyncio
from functools import lru_cache
from app.config import settings
from app.ai.vector_store import init_vector_store
from app.ai.dense import get_embedding_model
from app.ai.sparse import text_to_sparse
from app.ai.reranker import rerank_documents
from qdrant_client.models import Filter as QdrantFilter, FieldCondition, MatchValue
from qdrant_client.http.models import Prefetch, FusionQuery, Fusion


@lru_cache(maxsize=1)
def get_store():
    return init_vector_store()


@lru_cache(maxsize=1)
def get_embed_model():
    return get_embedding_model()


async def retrieve_relevant_documents(query: str, k: int = 10, tag: str | None = None, reranking: bool = False, rerank_k: int = 5) -> list[dict]:
    client = get_store()
    embed_model = get_embed_model()

    k = min(max(k, 1), 10)
    reranking = False

    query_dense, query_sparse = await asyncio.gather(
        embed_model.aembed_query(query),
        asyncio.to_thread(text_to_sparse, query),
    )

    qfilter = None
    if tag is not None:
        qfilter = QdrantFilter(must=[FieldCondition(key="tag", match=MatchValue(value=tag))])

    results = client.query_points(
        collection_name=settings.qdrant_collection,
        prefetch=[
            Prefetch(query=query_dense, using="", limit=k * 4),
            Prefetch(query=query_sparse, using="bm25", limit=k * 4),
        ],
        query=FusionQuery(fusion=Fusion.RRF),
        query_filter=qfilter,
        limit=k,
        with_payload=True,
    )

    docs = [
        {"text": p.payload.pop("text"), "metadata": p.payload}
        for p in results.points
    ]

    if reranking and docs:
        docs = await rerank_documents(query, docs, top_k=rerank_k)

    if not docs:
        return [{"text": "No matching documents found for this query.", "metadata": {}}]

    return docs
