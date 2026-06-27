"""Configuration — re-exports from existing config for backward compat."""
import os
from typing import Optional
from backend.config import (
    GROQ_API_KEY, GROQ_MODEL, GROQ_BASE_URL,
    GEMINI_API_KEY, GEMINI_MODEL,
    OPENCODE_API_KEY, OPENCODE_MODEL, OPENCODE_BASE_URL,
    OLLAMA_BASE_URL, OLLAMA_MODEL,
    BRAIN_NOTES, KNOWLEDGE_DIRS, PERSONALITY_PATH,
)

# Re-export all config values for new architecture modules
__all__ = [
    "GROQ_API_KEY", "GROQ_MODEL", "GROQ_BASE_URL",
    "GEMINI_API_KEY", "GEMINI_MODEL",
    "OPENCODE_API_KEY", "OPENCODE_MODEL", "OPENCODE_BASE_URL",
    "OLLAMA_BASE_URL", "OLLAMA_MODEL",
    "BRAIN_NOTES", "KNOWLEDGE_DIRS", "PERSONALITY_PATH",
    "get_provider_configs",
]


def get_provider_configs() -> list[dict]:
    """Return list of configured LLM provider configs for racing."""
    providers = []
    if OPENCODE_API_KEY:
        providers.append({
            "name": "opencode",
            "api_key": OPENCODE_API_KEY,
            "base_url": OPENCODE_BASE_URL,
            "model": OPENCODE_MODEL,
            "priority": 1,
        })
    if GROQ_API_KEY:
        providers.append({
            "name": "groq",
            "api_key": GROQ_API_KEY,
            "base_url": GROQ_BASE_URL,
            "model": GROQ_MODEL,
            "priority": 2,
        })
    if GEMINI_API_KEY:
        providers.append({
            "name": "gemini",
            "api_key": GEMINI_API_KEY,
            "model": GEMINI_MODEL,
            "priority": 3,
        })
    if OLLAMA_BASE_URL:
        providers.append({
            "name": "ollama",
            "api_key": "ollama",
            "base_url": OLLAMA_BASE_URL + "/v1",
            "model": OLLAMA_MODEL,
            "priority": 4,
        })
    providers.sort(key=lambda p: p["priority"])
    return providers
