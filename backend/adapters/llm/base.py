"""Base class for OpenAI-compatible LLM providers."""
from typing import Optional
from backend.ports.llm import LLMProvider
from backend.infrastructure.logger import get_logger

logger = get_logger("adapters.llm.base")


class OpenAICompatibleProvider(LLMProvider):
    """Base for any OpenAI-compatible API (OpenCode, Groq, Ollama)."""

    def __init__(self, name: str, api_key: str, base_url: str, model: str):
        self._name = name
        self._api_key = api_key
        self._base_url = base_url
        self._model = model

    @property
    def name(self) -> str:
        return self._name

    async def generate(self, messages: list[dict], max_tokens: int = 1024,
                       temperature: float = 0.7, timeout: float = 30.0) -> Optional[str]:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self._api_key, base_url=self._base_url, timeout=timeout)
            resp = client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            text = resp.choices[0].message.content
            if text:
                logger.debug("[%s] Generated %d tokens", self._name, len(text))
                return text
            return None
        except Exception as e:
            logger.warning("[%s] Generation failed: %s", self._name, e)
            return None
