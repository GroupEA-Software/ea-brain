from fastapi import APIRouter
from backend.brain_manager import list_notes, get_connections_files, get_inbox_files
from backend.vector_store import get_stats, rebuild_index as vs_rebuild
from backend.agents import get_status, run_connector, run_evolver

router = APIRouter(prefix="/api")


@router.get("/agents/status")
async def api_agent_status():
    return get_status()


@router.post("/agents/run-connector")
async def api_run_connector():
    result = await run_connector()
    return result


@router.post("/agents/run-evolver")
async def api_run_evolver():
    result = await run_evolver()
    return result


@router.get("/brain/stats")
async def api_brain_stats():
    notes = await list_notes()
    vector_stats = get_stats()
    connections = await get_connections_files()
    inbox = await get_inbox_files()
    return {
        "total_notes": len(notes),
        "total_connections": len(connections),
        "total_vectors": vector_stats["vectors"],
        "inbox_pending": len(inbox),
        "agents": get_status(),
    }


@router.get("/health")
async def health():
    from datetime import datetime
    return {"status": "ok", "time": datetime.now().isoformat()}


@router.post("/brain/rebuild")
async def api_rebuild():
    count = await vs_rebuild()
    return {"status": "ok", "documents_indexed": count}
