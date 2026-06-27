"""Groq provider — Llama/Mixtral free tier."""
from backend.adapters.llm.base import OpenAICompatibleProvider
from backend.infrastructure.config import GROQ_API_KEY, GROQ_BASE_URL, GROQ_MODEL


class GroqProvider(OpenAICompatibleProvider):
    """Groq — free Llama/Mixtral inference."""

    def __init__(self):
        super().__init__(
            name="groq",
            api_key=GROQ_API_KEY or "",
            base_url=GROQ_BASE_URL,
            model=GROQ_MODEL,
        )
