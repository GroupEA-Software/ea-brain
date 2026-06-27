"""
app.py — Application wiring (DI container + startup).
Connects domain entities, ports, adapters, and use cases.
"""
from pathlib import Path

from backend.infrastructure.config import (
    BRAIN_NOTES, PERSONALITY_PATH, get_provider_configs,
)
from backend.infrastructure.container import Container, container
from backend.infrastructure.logger import get_logger, silence_noisy_loggers
from backend.ports.repositories import NoteRepository, PersonalityRepository
from backend.ports.search import VectorSearchPort, WebSearchPort
from backend.ports.llm import LLMRouter
from backend.adapters.filesystem.notes import FileSystemNoteRepository
from backend.adapters.filesystem.personality import FileSystemPersonalityRepository
from backend.adapters.filesystem.vector_store import FileSystemVectorStore
from backend.adapters.llm.router import ConcurrentLLMRouter
from backend.adapters.llm.local import LocalFallbackProvider
from backend.application.personality import PersonalityService
from backend.application.search import SearchService
from backend.application.chat import ChatService
from backend.application.quiz import QuizService

logger = get_logger("application.app")
_built = False


def build_providers() -> list:
    """Build LLM providers from config, with local fallback last."""
    from backend.adapters.llm.opencode import OpenCodeProvider
    from backend.adapters.llm.groq import GroqProvider
    from backend.adapters.llm.gemini import GeminiProvider

    provider_map = {
        "opencode": lambda c: OpenCodeProvider(),
        "groq": lambda c: GroqProvider(),
        "gemini": lambda c: GeminiProvider(),
    }

    providers = []
    configs = get_provider_configs()
    for cfg in configs:
        builder = provider_map.get(cfg["name"])
        if builder:
            try:
                providers.append(builder(cfg))
            except Exception as e:
                logger.warning("Failed to init provider '%s': %s", cfg["name"], e)

    # Local fallback is always available
    providers.append(LocalFallbackProvider())
    return providers


def ensure_built() -> Container:
    """Build container once on first call."""
    global _built
    if _built:
        return container

    silence_noisy_loggers()

    # BRAIN_NOTES = brain/baul/, path root is brain/
    brain_root = BRAIN_NOTES.parent  # brain/
    meta_dir = brain_root / "meta"
    notes_dir = BRAIN_NOTES / "notes"  # brain/baul/notes/

    # ── Adapters ──
    note_repo = FileSystemNoteRepository(brain_root, {})
    personality_repo = FileSystemPersonalityRepository(PERSONALITY_PATH)
    vector_store = FileSystemVectorStore(meta_dir, notes_dir)

    # ── LLM ──
    providers = build_providers()
    llm_router = ConcurrentLLMRouter(providers)
    logger.info("LLM router ready: %d providers (%s)",
                len(providers), ", ".join(p.name for p in providers))

    # ── Services ──
    personality_svc = PersonalityService(personality_repo)
    search_svc = SearchService(vector_store, None)
    chat_svc = ChatService(llm_router, vector_store, None, note_repo, personality_svc)
    quiz_svc = QuizService(llm_router, vector_store)

    # ── Register ──
    container.register(NoteRepository, note_repo)
    container.register(PersonalityRepository, personality_repo)
    container.register(VectorSearchPort, vector_store)
    container.register(LLMRouter, llm_router)
    container.register(PersonalityService, personality_svc)
    container.register(ChatService, chat_svc)
    container.register(QuizService, quiz_svc)
    container.register(SearchService, search_svc)

    _built = True
    logger.info("Application container built successfully")
    return container
