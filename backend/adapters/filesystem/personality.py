"""FileSystemPersonalityRepository — reads/writes personality as JSON."""
import json
from pathlib import Path
from typing import Optional

from backend.domain.models import Personality
from backend.domain.exceptions import PersonalityNotFoundError
from backend.ports.repositories import PersonalityRepository
from backend.infrastructure.logger import get_logger

logger = get_logger("adapters.fs.personality")


class FileSystemPersonalityRepository(PersonalityRepository):
    """Stores personality state as a single JSON file."""

    def __init__(self, path: Path):
        self._path = path
        self._lock = None  # lazy init

    async def _get_lock(self):
        if self._lock is None:
            import asyncio
            self._lock = asyncio.Lock()
        return self._lock

    async def load(self) -> Optional[Personality]:
        async with await self._get_lock():
            try:
                if not self._path.exists():
                    return None
                data = json.loads(self._path.read_text(encoding="utf-8"))
                return Personality(
                    interactions_count=data.get("interactions_count", 0),
                    user_traits=data.get("user_traits", []),
                    favorite_topics=data.get("favorite_topics", []),
                    language_preference=data.get("language_preference", "es"),
                    catchphrases=data.get("catchphrases", []),
                    memory=data.get("memory", []),
                    last_topics=data.get("last_topics", []),
                )
            except (json.JSONDecodeError, OSError) as e:
                logger.error("Failed to load personality: %s", e)
                return None

    async def save(self, personality: Personality) -> None:
        async with await self._get_lock():
            try:
                self._path.parent.mkdir(parents=True, exist_ok=True)
                data = {
                    "interactions_count": personality.interactions_count,
                    "user_traits": personality.user_traits,
                    "favorite_topics": personality.favorite_topics,
                    "language_preference": personality.language_preference,
                    "catchphrases": personality.catchphrases,
                    "memory": personality.memory,
                    "last_topics": personality.last_topics,
                }
                self._path.write_text(
                    json.dumps(data, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
                logger.debug("Personality saved (%d interactions)", personality.interactions_count)
            except OSError as e:
                logger.error("Failed to save personality: %s", e)
                raise
