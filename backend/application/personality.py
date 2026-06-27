"""Personality use case — load, update, save personality state."""
from backend.domain.models import Personality
from backend.ports.repositories import PersonalityRepository
from backend.infrastructure.logger import get_logger

logger = get_logger("application.personality")


class PersonalityService:
    """Manages the EAgis evolving personality."""

    def __init__(self, repo: PersonalityRepository):
        self._repo = repo
        self._cached: Personality | None = None

    async def load(self) -> Personality:
        """Load personality, creating default if none exists."""
        if self._cached:
            return self._cached
        personality = await self._repo.load()
        if personality is None:
            personality = Personality()
            await self._repo.save(personality)
        self._cached = personality
        return personality

    async def update(self, message: str, answer: str, lang: str,
                     topics: list[str]) -> Personality:
        """Record an interaction and update traits/topics."""
        personality = await self.load()
        personality.record_interaction()

        # Extract traits from current interaction
        traits = _extract_traits(message, answer, lang)
        for t in traits:
            personality.add_trait(t)

        for t in topics:
            personality.add_topic(t)

        await self._repo.save(personality)
        self._cached = personality
        return personality

    async def reset(self) -> Personality:
        """Reset to factory defaults."""
        personality = Personality()
        await self._repo.save(personality)
        self._cached = personality
        return personality

    def invalidate_cache(self) -> None:
        self._cached = None


def _extract_traits(message: str, answer: str, lang: str) -> list[str]:
    """Simple trait extraction from user message."""
    traits = []
    msg_lower = message.lower()
    topics_map = {
        "programación": ["programación", "codigo", "código", "code", "programming",
                        "algoritmo", "algorithm", "python", "javascript", "typescript",
                        "go", "rust", "c#", "java"],
        "arquitectura": ["arquitectura", "architecture", "design pattern", "clean",
                        "hexagonal", "ddd", "microservicios", "microservices"],
        "matematicas": ["matematica", "matemática", "math", "algebra", "calculo",
                       "cálculo", "estadistica", "estadística"],
        "historia": ["historia", "history", "argentina", "guerra", "revolucion"],
        "ciencia": ["ciencia", "science", "fisica", "física", "quimica", "química",
                   "biologia", "biología"],
    }
    for topic, keywords in topics_map.items():
        if any(k in msg_lower for k in keywords):
            traits.append(f"interesado en {topic}")
            break
    return traits[:3]
