import asyncio
from typing import Any, Dict, List

from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.tools import tool
from sqlmodel import Session

from app.ai.retrieval import retrieve_relevant_documents
from app.config import settings
from app.database import engine
from app.log import log_call
from app.services.session import session_crud, session_lines

MAX_TOOL_LINES = 100
MAX_SEARCH_HITS = 20


def load_lines(session_id: int) -> list:
    with Session(engine) as db:
        db_session = session_crud.get_one(db, id=session_id)
        if not db_session:
            return []
        return session_lines(db, db_session)


@tool(description="""Search and retrieve relevant information from uploaded documents.

Use this tool when the user asks a question that may be answered by content in uploaded documents (PDF, TXT, MD files). The tool searches a vector database of document chunks and returns the most relevant passages.

- Always call this first for factual or knowledge-based questions.
- Do NOT use for general conversation, greetings, or simple Q&A that doesn't reference documents.
- If the first query returns nothing useful, try rephrasing the query.
- The `tag` parameter can be used to narrow search to documents with a specific tag.
- The `reranking` parameter enables cross-encoder reranking for improved relevance (default False).
- The `rerank_k` parameter controls how many results to keep after reranking (default 5).

Args:
    query (str): The user question refined for search. Translate to English if needed.
    k (int, optional): Number of results from hybrid search (default 10, max 20).
    tag (str, optional): Only search documents with this tag.
    reranking (bool, optional): Apply reranker after retrieval (default False).
    rerank_k (int, optional): Number of results after reranking (default 5).

Returns:
    list[dict]: Each item has "text" (str) and "metadata" (dict with filename, page, etc).
""")
async def retrieval_documents(query: str, k: int = 10, tag: str | None = None, reranking: bool = False, rerank_k: int = 5) -> list[dict]:
    query = str(query) if not isinstance(query, str) else query
    tag = str(tag) if tag and not isinstance(tag, str) else tag
    tag = None if tag in ("None", "none", "", "null", "nan") else tag

    try:
        results = await asyncio.wait_for(
            retrieve_relevant_documents(query, k, tag, reranking=reranking, rerank_k=rerank_k), timeout=300.0
        )
    except (asyncio.TimeoutError, Exception):
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


def format_lines(lines: List[Dict[str, Any]]) -> str:
    return "\n".join(f"{line.get('speaker', '?')}: {line.get('text', '')}" for line in lines)


@tool(description="""Get the index range of a session transcript.

Call this first when you need lines outside the injected context, so you know which start_index values are valid for get_more_messages.

Args:
    session_id (int): Session to read. Only use the current session id from your instructions.

Returns: total line count, first index (always 0), last index, and the speaker list.
""")
def transcript_info(session_id: int) -> str:
    all_lines = load_lines(session_id)
    if not all_lines:
        return "This session has no transcript lines."

    total = len(all_lines)
    speakers = sorted({str(line.get("speaker") or "?") for line in all_lines})
    return (
        f"This session transcript has {total} lines, "
        f"numbered {0}-{total - 1} (0 = oldest, {total - 1} = newest). "
        f"Speakers: {', '.join(speakers)}."
    )


@tool(description="""Read more lines from a session transcript by index.

Use transcript_info first to learn the valid index range. Lines are numbered from 0 (oldest) upward.

Args:
    session_id (int): Session to read. Only use the current session id from your instructions.
    start_index (int): First line number to read (use 0 to start from the oldest line).
    count (int): How many lines to read (max 100).
""")
def get_more_messages(session_id: int, start_index: int = 0, count: int = 50) -> str:
    all_lines = load_lines(session_id)
    start = max(0, int(start_index))
    end = min(len(all_lines), start + max(1, min(int(count), MAX_TOOL_LINES)))
    if start >= len(all_lines):
        return "No more lines: start_index is past the end of the transcript."

    chunk = all_lines[start:end]
    return f"Lines {start}-{end - 1} of {len(all_lines)}:\n" + format_lines(chunk)


@tool(description="""Search a session transcript for a keyword.

Use this to find what someone said about a topic, or who mentioned a word, without reading the whole transcript. Matching is case-insensitive.

Args:
    session_id (int): Session to search. Only use the current session id from your instructions.
    keyword (str): Word or phrase to search for (required, at least 2 characters).
""")
def search_transcript(session_id: int, keyword: str = "") -> str:
    all_lines = load_lines(session_id)
    needle = str(keyword or "").strip().lower()
    if len(needle) < 2:
        return "Give a keyword of at least 2 characters."

    hits = [i for i, line in enumerate(all_lines) if needle in str(line.get("text", "")).lower()]
    if not hits:
        return f"No line in this session mentions '{keyword.strip()}'."

    shown = hits[:MAX_SEARCH_HITS]
    out = [f"Found {len(hits)} line(s) mentioning '{keyword.strip()}':"]
    for i in shown:
        line = all_lines[i]
        out.append(f"[{i}] {line.get('speaker', '?')}: {line.get('text', '')}")
    if len(hits) > len(shown):
        out.append(f"...and {len(hits) - len(shown)} more. Use get_more_messages around those indexes.")

    return "\n".join(out)


TRANSCRIPT_TOOLS = [transcript_info, get_more_messages, search_transcript]
