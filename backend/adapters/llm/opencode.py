"""OpenCode Zen provider — DeepSeek V4 Flash Free."""
from backend.adapters.llm.base import OpenAICompatibleProvider
from backend.infrastructure.config import OPENCODE_API_KEY, OPENCODE_BASE_URL, OPENCODE_MODEL


class OpenCodeProvider(OpenAICompatibleProvider):
    """DeepSeek V4 Flash Free via OpenCode Zen — free, no API key needed."""

    def __init__(self):
        super().__init__(
            name="opencode",
            api_key=OPENCODE_API_KEY or "no-key-needed",
            base_url=OPENCODE_BASE_URL,
            model=OPENCODE_MODEL,
        )
