"""Search use case — multi-source search (vector + web)."""
from backend.ports.search import VectorSearchPort, WebSearchPort, SearchResult
from backend.infrastructure.logger import get_logger

logger = get_logger("application.search")

_STOPWORDS_ES = {"de", "la", "que", "el", "en", "y", "a", "los", "del", "se",
                 "las", "por", "un", "para", "con", "no", "una", "su", "al",
                 "lo", "como", "mas", "pero", "sus", "le", "ya", "este", "entre",
                 "porque", "cuando", "todo", "tambien"}


class SearchService:
    """Combines vector search with optional web fallback."""

    def __init__(self, vector_search: VectorSearchPort, web_search: WebSearchPort | None = None):
        self._vector = vector_search
        self._web = web_search

    async def search_brain(self, query: str, k: int = 5) -> list[SearchResult]:
        """Search the brain's vector index."""
        results = await self._vector.search(query, k)
        return self._rerank(query, results)

    async def search_web(self, query: str) -> str:
        """Fallback web search."""
        if not self._web:
            return ""
        try:
            return await self._web.search(query)
        except Exception as e:
            logger.warning("Web search failed: %s", e)
            return ""

    def _rerank(self, query: str, results: list[SearchResult]) -> list[SearchResult]:
        """Simple keyword overlap boost on top of vector score."""
        query_words = {
            w.strip(".,!?;:").lower()
            for w in query.split()
            if len(w) > 3 and w.lower() not in _STOPWORDS_ES
        }
        if not query_words:
            return results

        for r in results:
            keyword_overlap = sum(
                1 for w in query_words if w in r.filename.lower() or w in r.snippet.lower()
            )
            r.score += keyword_overlap * 0.05

        results.sort(key=lambda x: x.score, reverse=True)
        return results
