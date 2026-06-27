"""
knowledge.py — API routes for the knowledge library (01-07 directories).

These are the Cerebro-Digital knowledge directories: indexed, searchable,
and browsable in the frontend as a read-only knowledge library.
"""

from fastapi import APIRouter
from backend.brain_manager import list_knowledge, get_knowledge_note

router = APIRouter(prefix="/api/knowledge")


@router.get("")
async def api_list_knowledge():
    """List all knowledge categories with their files."""
    try:
        categories = await list_knowledge()
        total = sum(c["total"] for c in categories)
        return {"categories": categories, "total": total}
    except Exception as e:
        return {"error": str(e), "categories": [], "total": 0}


@router.get("/{filename:path}")
async def api_get_knowledge_note(filename: str):
    """Get full content of a knowledge note."""
    note = await get_knowledge_note(filename)
    if not note:
        return {"error": "Nota de conocimiento no encontrada"}, 404
    return note
