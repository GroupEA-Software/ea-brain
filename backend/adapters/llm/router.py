"""Concurrent LLM provider router — race providers, take first response.

Instead of trying providers sequentially (which can cause 5+ minutes of latency
when the first provider is slow or rate-limited), this fires ALL configured
providers concurrently and returns the first successful response.

Design:
- asyncio.gather() with return_exceptions=True
- Wrap each provider in a task with the specified timeout
- Return first non-None result
- Log which provider won the race
"""
import asyncio
from typing import Optional

from backend.ports.llm import LLMProvider, LLMRouter
from backend.infrastructure.logger import get_logger

logger = get_logger("adapters.llm.router")


class ConcurrentLLMRouter(LLMRouter):
    """Races all available providers concurrently, returns first response."""

    def __init__(self, providers: list[LLMProvider]):
        if not providers:
            raise ValueError("At least one LLM provider is required")
        self._providers = providers

    @property
    def provider_count(self) -> int:
        return len(self._providers)

    async def race(self, messages: list[dict], max_tokens: int = 1024,
                   temperature: float = 0.7, timeout: float = 30.0) -> Optional[str]:
        """Fire all providers in parallel, return first successful response.

        Args:
            messages: Chat messages in OpenAI format
            max_tokens: Maximum tokens to generate
            temperature: Generation temperature
            timeout: Per-provider timeout in seconds

        Returns:
            Response text from the first provider that responds, or None if all fail.
        """
        if not self._providers:
            logger.error("No LLM providers configured")
            return None

        async def _race_provider(provider: LLMProvider) -> Optional[tuple[str, str]]:
            """Wrap a single provider call with timeout. Returns (name, text) or None."""
            try:
                result = await asyncio.wait_for(
                    provider.generate(messages, max_tokens, temperature, timeout),
                    timeout=timeout,
                )
                if result:
                    return (provider.name, result)
                return None
            except asyncio.TimeoutError:
                logger.debug("[%s] Timed out after %.1fs", provider.name, timeout)
                return None
            except Exception as e:
                logger.debug("[%s] Error: %s", provider.name, e)
                return None

        # Fire all providers concurrently
        tasks = [_race_provider(p) for p in self._providers]
        done, pending = await asyncio.wait(
            tasks,
            return_when=asyncio.FIRST_COMPLETED,
            timeout=timeout + 5.0,  # extra buffer for scheduling
        )

        # Cancel remaining pending tasks
        for task in pending:
            task.cancel()

        # Find first successful result among completed tasks
        for task in done:
            try:
                result = task.result()
                if result:
                    provider_name, text = result
                    logger.info("Provider '%s' won the race (%d chars)",
                                provider_name, len(text))
                    return text
            except Exception:
                continue

        # All providers failed — try gathering remaining exceptions for logging
        logger.error("All %d LLM providers failed for this request", len(self._providers))
        return None
