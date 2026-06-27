import os
import json
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response

from backend.config import BRAIN_NOTES, BRAIN_INBOX, BRAIN_CONNECTIONS, BRAIN_META
from backend.vector_store import rebuild_index
from backend.routes.notes import router as notes_router
from backend.routes.inbox import router as inbox_router
from backend.routes.export import router as export_router
from backend.routes.chat import router as chat_router
from backend.routes.graph import router as graph_router
from backend.routes.brain import router as brain_router
from backend.routes.repos import router as repos_router
from backend.routes.knowledge import router as knowledge_router
from backend.routes.personality import router as personality_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[Baul] Super Cerebro iniciando...")
    count = await rebuild_index()
    print(f"[Baul] Indice vectorial reconstruido: {count} documentos")
    from backend.config import CONNECTOR_INTERVAL
    task = asyncio.create_task(_auto_connector())
    yield
    task.cancel()
    print("[Baul] Apagado.")


async def _auto_connector():
    from backend.config import CONNECTOR_INTERVAL, EVOLVER_INTERVAL
    from backend.agents import run_connector, run_evolver
    conn_interval = max(CONNECTOR_INTERVAL, 60)
    evol_interval = max(EVOLVER_INTERVAL, 120)
    conn_cycles = 0
    while True:
        await asyncio.sleep(conn_interval)
        try:
            conn_cycles += 1
            result = await run_connector()
            found = result.get("connections_found", 0)
            if found > 0:
                print(f"[Baul] Conector: {found} conexiones semanticas escritas")
                await rebuild_index()
            else:
                print(f"[Baul] Conector: analizo {result.get('notes_analyzed', 0)} notas")
            if conn_cycles % (evol_interval // conn_interval) == 0:
                evol = await run_evolver()
                if evol.get("tags_found", 0) > 0:
                    print(f"[Baul] Evolucionador: {evol['tags_found']} tags")
        except Exception as e:
            print(f"[Baul] Auto-connector error: {e}")


app = FastAPI(title="Baul - Super Cerebro", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(notes_router)
app.include_router(inbox_router)
app.include_router(export_router)
app.include_router(chat_router)
app.include_router(graph_router)
app.include_router(brain_router)
app.include_router(repos_router)
app.include_router(knowledge_router)
app.include_router(personality_router)


# WebSocket for real-time chat

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()
    history = []
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            user_msg = msg.get("message", "")
            from backend.rag import ask as rag_ask
            result = await rag_ask(user_msg, history)
            history.append({"role": "user", "content": user_msg})
            history.append({"role": "assistant", "content": result["answer"]})
            await websocket.send_text(json.dumps({
                "type": "response",
                "answer": result["answer"],
                "sources": result["sources"],
                "connections": result["connections"],
            }))
    except WebSocketDisconnect:
        pass


# Serve uploaded images from brain/baul/

BRAIN_DIR = Path(__file__).parent.parent / "brain"


@app.get("/api/images/{path:path}")
async def serve_image(path: str):
    file_path = BRAIN_DIR / "baul" / path
    if file_path.exists() and file_path.is_file():
        ext = file_path.suffix.lower()
        media_types = {
            ".webp": "image/webp", ".png": "image/png", ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg", ".gif": "image/gif", ".bmp": "image/bmp",
            ".svg": "image/svg+xml",
        }
        return FileResponse(str(file_path), media_type=media_types.get(ext))
    return Response(status_code=404)


# Static files (frontend)

FRONTEND_DIR = Path(__file__).parent.parent / "frontend" / "dist"


@app.get("/")
async def serve_index():
    return FileResponse(str(FRONTEND_DIR / "index.html"))


@app.get("/{path:path}")
async def serve_static(path: str):
    file_path = FRONTEND_DIR / path
    if file_path.exists() and file_path.is_file():
        return FileResponse(str(file_path))
    return FileResponse(str(FRONTEND_DIR / "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)
