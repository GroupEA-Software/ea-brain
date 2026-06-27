import json
import asyncio
import logging
from fastapi import APIRouter, Form
from backend.rag import ask as rag_ask
from backend.vector_store import search
from backend.evolution import (
    consolidate_from_conversation,
    save_connections,
    get_evolution_stats,
    background_evolution_loop,
    stop_background_evolution,
)

logger = logging.getLogger("baul.chat")
router = APIRouter(prefix="/api")

# Keep last conversation for evolution learning
_last_conversation: list = []


@router.on_event("startup")
async def start_evolution():
    asyncio.create_task(background_evolution_loop(interval_seconds=1800))
    logger.info("[Chat] Background evolution loop started")


@router.on_event("shutdown")
def stop_evolution():
    stop_background_evolution()
    logger.info("[Chat] Background evolution loop stopped")


@router.post("/search")
async def api_search(query: str = Form(""), k: int = Form(5)):
    results = await search(query, k)
    return {"results": results}


@router.post("/chat")
async def api_chat(message: str = Form(""), history: str = Form("")):
    global _last_conversation
    hist = json.loads(history) if history else None

    try:
        result = await asyncio.wait_for(rag_ask(message, hist), timeout=2.5)
    except asyncio.TimeoutError:
        result = {
            "answer": "(Respuesta rápida local — EAgis está meditando) No tengo una respuesta completa, pero revisá tus notas manualmente.",
            "sources": [],
            "connections": [],
            "web_search_used": False,
            "suggest_save": False,
        }

    # --- Autonomous learning: consolidate from conversation ---
    if hist:
        _last_conversation = hist[-6:] + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": result.get("answer", "")},
        ]
        # Fire-and-forget consolidation (non-blocking)
        asyncio.create_task(_learn_from_conversation())

    return result


async def _learn_from_conversation():
    """Non-blocking evolution trigger."""
    global _last_conversation
    try:
        draft = await consolidate_from_conversation(_last_conversation)
        if draft:
            logger.info(f"[Evolution] Created draft note from conversation: {draft}")
    except Exception as e:
        logger.warning(f"[Evolution] Consolidation skipped: {e}")


@router.get("/evolution/stats")
async def evolution_stats():
    return get_evolution_stats()
