import asyncio

from langchain_core.tools import tool

from app.log import log_call
from app.ai.retrieval import retrieve_relevant_documents
from app.config import settings

from langchain_community.tools.tavily_search import TavilySearchResults


@tool(description="""Search and retrieve relevant information from uploaded documents.

Use this tool when the user asks a question that may be answered by content in uploaded documents (PDF, TXT, MD files). The tool searches a vector database of document chunks and returns the most relevant passages.

- Always call this first for factual or knowledge-based questions.
- Do NOT use for general conversation, greetings, or simple Q&A that doesn't reference documents.
- If the first query returns nothing useful, try rephrasing the query.
- The `tag` parameter can be used to narrow search to documents with a specific tag.
- The `reranking` parameter enables cross-encoder reranking for improved relevance (default True).
- The `rerank_k` parameter controls how many results to keep after reranking (default 10).

Args:
    query (str): The user question refined for search. Translate to English if needed.
    k (int, optional): Number of results from hybrid search (default 5, min 20 for reranking).
    tag (str, optional): Only search documents with this tag.
    reranking (bool, optional): Apply reranker after retrieval (default True).
    rerank_k (int, optional): Number of results after reranking (default 10).

Returns:
    list[dict]: Each item has "text" (str) and "metadata" (dict with filename, page, etc).
""")
async def retrieval_documents(query: str, k: int = 20, tag: str | None = None, reranking: bool = True, rerank_k: int = 10) -> list[dict]:
    query = str(query) if not isinstance(query, str) else query
    tag = str(tag) if tag and not isinstance(tag, str) else tag
    tag = None if tag in ("None", "none", "", "null", "nan") else tag

    try:
        results = await asyncio.wait_for(
            retrieve_relevant_documents(query, k, tag, reranking=reranking, rerank_k=rerank_k), timeout=300.0
        )
    except asyncio.TimeoutError:
        results = []

    log_call("retrieval_documents", {"query": query, "k": k, "tag": tag, "reranking": reranking, "rerank_k": rerank_k}, results)
    return results



@tool(description="""Search the web for current, up-to-date information.

Use this tool when the user asks about current events, recent news, or information that may have changed since the documents were uploaded. Also use it to supplement document retrieval when the uploaded documents don't contain enough information.

- Always use for questions about recent events, real-time data, or rapidly changing topics.
- Formulate the query in English for best results.
- Returns a list of search result snippets with titles, URLs, and content.

Args:
    query (str): The search query. Rewrite in English for best results.

Returns:
    list[dict]: Each item has "title", "url", and "content" fields.
""")
async def web_search(query: str, k: int = 10) -> list[dict]:
    if not settings.tavily_api_key:
        return [{"title": "Not configured", "url": "", "content": "Web search requires a Tavily API key. Please set TAVILY_API_KEY in your environment."}]

    tavily = TavilySearchResults(api_key=settings.tavily_api_key, max_results=k)

    try:
        results = await tavily.ainvoke({"query": query})
    except Exception as e:
        results = [{"title": "Search failed", "url": "", "content": f"Web search error: {e}"}]

    log_call("web_search", {"query": query}, results)
    return results
