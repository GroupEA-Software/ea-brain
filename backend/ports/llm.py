from abc import ABC, abstractmethod
from typing import Optional


class LLMProvider(ABC):
    """Interface for a single LLM provider."""

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    async def generate(self, messages: list[dict], max_tokens: int = 1024,
                       temperature: float = 0.7, timeout: float = 30.0) -> Optional[str]:
        """Send messages, return response text or None on failure."""
        ...


class LLMRouter(ABC):
    """Interface for provider routing with racing."""

    @abstractmethod
    async def race(self, messages: list[dict], max_tokens: int = 1024,
                   temperature: float = 0.7, timeout: float = 30.0) -> Optional[str]:
        """Race multiple providers concurrently, return first successful response."""
        ...
