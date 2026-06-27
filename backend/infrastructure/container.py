"""Simple dependency injection container.

Usage:
    container = Container()
    container.register(NoteRepository, FileSystemNoteRepository())
    repo = container.resolve(NoteRepository)
"""
from typing import Any, Type


class Container:
    """Minimal DI container — register implementations, resolve by interface."""

    def __init__(self):
        self._registry: dict[type, Any] = {}

    def register(self, interface: type, implementation: Any) -> None:
        self._registry[interface] = implementation

    def resolve(self, interface: type) -> Any:
        impl = self._registry.get(interface)
        if impl is None:
            raise KeyError(f"No implementation registered for {interface.__name__}")
        return impl

    def has(self, interface: type) -> bool:
        return interface in self._registry


# Global singleton
container = Container()
