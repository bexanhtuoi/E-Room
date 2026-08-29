import asyncio
from langchain_openai import OpenAIEmbeddings
from app.config import settings
from app.log import get_logger

log = get_logger(__name__, log_file="log/embed.log")


def get_embedding_model(timeout: int = 300) -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model=settings.embedding_model,
        base_url=settings.embedding_base_url or settings.llm_base_url,
        api_key=settings.embedding_api_key or settings.llm_api_key,
        check_embedding_ctx_length=False,
        timeout=timeout,
    )


async def text_embedding(text: str, embed_model: OpenAIEmbeddings) -> list[float]:
    return await embed_model.aembed_query(text)


def documents_embedding(documents: list[str], embed_model: OpenAIEmbeddings) -> list[list[float]]:
    return embed_model.embed_documents(documents)


async def batch_embed(embed_model, texts, batch_size=8):
    results = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        try:
            chunk = await asyncio.wait_for(
                asyncio.to_thread(embed_model.embed_documents, batch),
                timeout=120,
            )
            results.extend(chunk)
        except asyncio.TimeoutError:
            log.warning(f"[batch_embed] batch {i//batch_size} timeout, retrying...")
            chunk = await asyncio.wait_for(
                asyncio.to_thread(embed_model.embed_documents, batch),
                timeout=180,
            )
            results.extend(chunk)
    return results
