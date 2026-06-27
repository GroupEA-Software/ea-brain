"""
personality.py — API routes for EAgis personality state.
- GET  /api/personality      -> return full personality state
- POST /api/personality/reset -> reset to default factory state
"""

import json
from fastapi import APIRouter
from backend.config import PERSONALITY_PATH
from backend.rag import _default_personality, _save_personality

router = APIRouter(prefix="/api")


@router.get("/personality")
async def get_personality():
    """Return the full EAgis personality state."""
    try:
        if PERSONALITY_PATH.exists():
            data = json.loads(PERSONALITY_PATH.read_text(encoding="utf-8"))
            return data
    except Exception:
        pass
    # No personality file yet — return default
    return _default_personality()


@router.post("/personality/reset")
async def reset_personality():
    """Reset EAgis personality to factory defaults."""
    fresh = _default_personality()
    _save_personality(fresh)
    return {"status": "ok", "message": "Personality reset to defaults", "personality": fresh}
