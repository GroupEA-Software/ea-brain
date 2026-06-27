from abc import ABC, abstractmethod
from typing import Optional


class SearchResult:
    """Value object for search results."""
    def __init__(self, filename: str, score: float, snippet: str = ""):
        self.filename = filename
        self.score = score
        self.snippet = snippet


class VectorSearchPort(ABC):
    """Interface for vector similarity search."""

    @abstractmethod
    async def search(self, query: str, k: int = 5) -> list[SearchResult]:
        ...

    @abstractmethod
    async def add_document(self, filename: str, content: str) -> None:
        ...

    @abstractmethod
    async def remove_document(self, filename: str) -> None:
        ...

    @abstractmethod
    async def rebuild(self) -> None:
        ...


class WebSearchPort(ABC):
    """Interface for web fallback search."""

    @abstractmethod
    async def search(self, query: str) -> str:
        """Return text content from web search results."""
        ...
