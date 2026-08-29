import httpx
from app.config import settings
from app.log import get_logger

log = get_logger("reranker", log_file="log/reranker.log")


async def rerank_documents(
    query: str,
    documents: list[dict],
    top_k: int = 10,
) -> list[dict]:
    if not documents:
        return documents

    base_url = settings.reranker_base_url or settings.llm_base_url
    api_key = settings.reranker_api_key or settings.llm_api_key
    model = settings.reranker_model
    if not model:
        log.warning("No reranker model configured, returning raw docs")
        return documents[:top_k]

    texts = [d["text"] for d in documents]
    total_chars = sum(len(t) for t in texts)
    url = f"{base_url.rstrip('/')}/rerank"

    log.info("Reranking %d docs (query_len=%d, total_chars=%d)", len(documents), len(query.split()), total_chars)

    try:
        async with httpx.AsyncClient(timeout=300) as client:
            resp = await client.post(
                url,
                json={"model": model, "query": query, "documents": texts, "top_k": top_k},
                headers={"Authorization": f"Bearer {api_key}"},
            )
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        if not results:
            log.warning("Reranker returned empty results, fallback to raw order")
            return documents[:top_k]

        reranked = []
        for r in results:
            idx = r.get("index")
            score = r.get("relevance_score", 0)
            if idx is not None and idx < len(documents):
                doc = dict(documents[idx])
                doc["rerank_score"] = score
                reranked.append(doc)
        reranked.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
        top_scores = [f"{d.get('rerank_score', 0):.4f}" for d in reranked[:5]]
        log.info("Rerank OK: %d results, top scores=[%s]", len(results), ", ".join(top_scores))
        return reranked[:top_k]
    except httpx.HTTPStatusError as e:
        body = ""
        try:
            body = str(e.response.json().get("error", {}).get("message", ""))[:200]
        except Exception:
            body = str(e.response.content[:200])
        log.error("Reranker HTTP %d: %s", e.response.status_code, body)
        return documents[:top_k]
    except httpx.TimeoutException:
        log.error("Reranker timeout after 300s")
        return documents[:top_k]
    except Exception as e:
        log.error("Reranker exception: %s: %s", type(e).__name__, str(e)[:200])
        return documents[:top_k]
