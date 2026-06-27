import asyncio
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.repo_sync import (
    list_repos,
    connect_repo,
    sync_repo,
    sync_all,
    disconnect_repo,
    check_updates,
)

logger = logging.getLogger("baul.routes.repos")
router = APIRouter(prefix="/api/repos")


class ConnectRequest(BaseModel):
    url: str
    branch: str = "main"
    token: str = ""
    repo_path: str = ""


class SyncRequest(BaseModel):
    repo_id: str = ""
    token: str = ""


class DisconnectRequest(BaseModel):
    repo_id: str
    remove_files: bool = False


@router.get("")
async def api_list_repos():
    try:
        repos = list_repos()
        return {"repos": repos}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/check-updates")
async def api_check_updates():
    try:
        updates = check_updates()
        return {"updates": updates}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/connect")
async def api_connect_repo(req: ConnectRequest):
    try:
        result = await connect_repo(
            url=req.url,
            branch=req.branch,
            token=req.token,
            repo_path=req.repo_path,
        )
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))
    except RuntimeError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.exception("Connect error")
        raise HTTPException(500, str(e))


@router.post("/sync")
async def api_sync_repo(req: SyncRequest):
    try:
        if req.repo_id == "all":
            results = await sync_all(token=req.token)
            return {"results": results}
        result = await sync_repo(repo_id=req.repo_id, token=req.token)
        return result
    except ValueError as e:
        raise HTTPException(404, str(e))
    except RuntimeError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.exception("Sync error")
        raise HTTPException(500, str(e))


@router.delete("")
async def api_disconnect_repo(repo_id: str, remove_files: bool = False):
    try:
        result = disconnect_repo(repo_id, remove_files)
        return result
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))
