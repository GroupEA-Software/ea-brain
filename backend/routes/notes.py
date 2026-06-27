from fastapi import APIRouter
from backend.brain_manager import list_notes, get_note, create_note, update_note, delete_note, move_note, list_folders, create_folder
from backend.vector_store import add_document

router = APIRouter(prefix="/api")


@router.get("/folders")
async def api_list_folders():
    return await list_folders()


@router.post("/folders")
async def api_create_folder(path: str = ""):
    return await create_folder(path)


@router.get("/notes")
async def api_list_notes():
    return await list_notes()


@router.get("/notes/{filename:path}")
async def api_get_note(filename: str):
    note = await get_note(filename)
    if not note:
        return {"error": "Nota no encontrada"}, 404
    return note


@router.post("/notes")
async def api_create_note(title: str = "", content: str = "", tags: str = "", folder: str = ""):
    tags_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    result = await create_note(title, content, tags_list, folder)
    await add_document(result["filename"], result["content"])
    return result


@router.put("/notes/{filename:path}")
async def api_update_note(filename: str, content: str = ""):
    result = await update_note(filename, content)
    await add_document(filename, content)
    return result


@router.put("/notes/{filename:path}/move")
async def api_move_note(filename: str, folder: str = ""):
    return await move_note(filename, folder)


@router.delete("/notes/{filename:path}")
async def api_delete_note(filename: str):
    return {"deleted": await delete_note(filename)}
