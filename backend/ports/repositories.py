from abc import ABC, abstractmethod
from typing import Optional
from backend.domain.models import Note, Personality


class NoteRepository(ABC):
    """Interface for note persistence."""

    @abstractmethod
    async def get(self, filename: str) -> Optional[Note]:
        ...

    @abstractmethod
    async def save(self, note: Note) -> str:
        """Save a note, return its filename."""
        ...

    @abstractmethod
    async def delete(self, filename: str) -> bool:
        ...

    @abstractmethod
    async def list_all(self, folder: str = "") -> list[Note]:
        ...

    @abstractmethod
    async def search_by_content(self, query: str) -> list[Note]:
        ...


class PersonalityRepository(ABC):
    """Interface for personality state persistence."""

    @abstractmethod
    async def load(self) -> Optional[Personality]:
        ...

    @abstractmethod
    async def save(self, personality: Personality) -> None:
        ...


class ConnectionRepository(ABC):
    """Interface for knowledge graph connections."""

    @abstractmethod
    async def get_connections(self, note_id: str) -> list[tuple[str, float]]:
        ...

    @abstractmethod
    async def save_connections(self, connections: list[tuple[str, str, float]]) -> None:
        ...

    @abstractmethod
    async def get_all(self) -> list[tuple[str, str, float]]:
        ...
