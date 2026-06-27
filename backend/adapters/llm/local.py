"""Local fallback provider — regex-based, no API call.

Used when all remote providers fail or are not configured.
Generates a simple response from context without any LLM call.
"""
from typing import Optional
from backend.ports.llm import LLMProvider
from backend.infrastructure.logger import get_logger

logger = get_logger("adapters.llm.local")


class LocalFallbackProvider(LLMProvider):
    """Last-resort local generator. No API key needed, no network."""

    @property
    def name(self) -> str:
        return "local-fallback"

    async def generate(self, messages: list[dict], max_tokens: int = 1024,
                       temperature: float = 0.7, timeout: float = 30.0) -> Optional[str]:
        """Generate a basic response from context in messages."""
        try:
            # Extract context from system message
            context = ""
            for msg in messages:
                if msg["role"] == "system" and "[[context]]" in msg.get("content", ""):
                    # Extract content between markers
                    import re
                    match = re.search(r"\[\[content\]\]\n(.+?)(?:\n---|\Z)", msg["content"], re.DOTALL)
                    if match:
                        context = match.group(1)[:500]
                    break

            notes = re.findall(r"\[\[([^\]]+)\]\]", context)
            notes = list(set(notes))[:5]

            base = "*EAgis adjusts his tie and clears his throat.*\n"
            base += "Quite. I've consulted the brain archives.\n\n"
            if context.strip():
                base += "**From your notes:**\n"
                for line in context.split("\n")[:5]:
                    if line.strip() and len(line) > 20:
                        base += f"- {line.strip()[:200]}\n"
                base += "\n"
            if notes:
                base += "**Relevant entries:**\n"
                base += "\n".join(f'- [[{n}]]' for n in notes) + "\n\n"
            base += "Do feed me some material to work with. I'm dreadfully underutilised."
            return base
        except Exception as e:
            logger.error("Local fallback failed: %s", e)
            return "I'm afraid I couldn't find anything useful in the archives. Try asking differently."
