"""
repo_sync.py — GitHub repo sync engine for Baul.

Connects external Git repos, imports .md files, detects updates,
and keeps the brain in sync.
"""

import re
import os
import json
import asyncio
import logging
import stat
import subprocess
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Optional

from backend.config import BRAIN_NOTES, BRAIN_META

logger = logging.getLogger("baul.repo_sync")

REPOS_META = BRAIN_META / "connected_repos.json"
TEMP_CLONE_DIR = BRAIN_META / "_repo_clones"


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def _load_repos() -> dict:
    if REPOS_META.exists():
        try:
            return json.loads(REPOS_META.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"repos": []}


def _save_repos(data: dict):
    REPOS_META.parent.mkdir(parents=True, exist_ok=True)
    REPOS_META.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _gen_repo_id(url: str) -> str:
    """Generate a short unique ID from a repo URL."""
    url = url.rstrip("/").rstrip(".git")
    parts = url.rstrip("/").split("/")
    return f"{parts[-2]}-{parts[-1]}" if len(parts) >= 2 else parts[-1]


def _rmtree(path: Path):
    """Windows-safe rmtree that handles read-only .git files."""
    import stat
    def _on_error(func, fpath, exc_info):
        # Make read-only files writable and retry
        try:
            os.chmod(fpath, stat.S_IWRITE)
            func(fpath)
        except Exception:
            pass
    if path.exists():
        shutil.rmtree(str(path), onerror=_on_error)


# ---------------------------------------------------------------------------
# Git operations
# ---------------------------------------------------------------------------

def _run_git(args: list, cwd: Optional[Path] = None, timeout: int = 60) -> str:
    """Run a git command and return stdout."""
    result = subprocess.run(
        ["git"] + args,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout.strip()


def _get_remote_commit(url: str, branch: str = "main") -> Optional[str]:
    """Get the latest commit hash from a remote repo."""
    try:
        output = _run_git(["ls-remote", url, f"refs/heads/{branch}"], timeout=30)
        if output:
            return output.split()[0]
    except Exception as e:
        logger.warning(f"Cannot reach remote {url}: {e}")
    return None


def _clone_repo(url: str, dest: Path, branch: str = "main", token: str = "") -> int:
    """Clone a repo with depth=1 into dest. Returns file count."""
    if token:
        # Insert token into URL for auth
        if "://" in url:
            protocol, rest = url.split("://", 1)
            url = f"{protocol}://{token}@{rest}"
        else:
            url = f"https://{token}@{url}"

    if dest.exists():
        _rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    _run_git(["clone", "--depth", "1", "--branch", branch, url, str(dest)], timeout=120)

    count = 0
    for f in dest.rglob("*"):
        if f.is_file():
            count += 1
    return count


# ---------------------------------------------------------------------------
# File import
# ---------------------------------------------------------------------------

_MD_EXTENSIONS = {".md", ".markdown", ".mdown", ".mkd"}
_TXT_EXTENSIONS = {".txt", ".csv", ".json", ".yaml", ".yml"}


def _import_files(repo_id: str, clone_dir: Path, repo_path: str = "") -> List[str]:
    """Copy .md files from cloned repo into brain/baul/<repo_id>/.

    Returns list of imported filenames (relative to BRAIN_NOTES).
    """
    import aiofiles

    source_dir = clone_dir
    if repo_path:
        source_dir = clone_dir / repo_path
        if not source_dir.exists():
            raise FileNotFoundError(f"Path '{repo_path}' not found in repo")

    target_base = BRAIN_NOTES / repo_id
    target_base.mkdir(parents=True, exist_ok=True)

    imported = []
    for f in sorted(source_dir.rglob("*")):
        if not f.is_file():
            continue
        ext = f.suffix.lower()
        if ext not in _MD_EXTENSIONS and ext not in _TXT_EXTENSIONS:
            continue

        rel = f.relative_to(source_dir)
        target = target_base / rel
        target.parent.mkdir(parents=True, exist_ok=True)

        # Only copy if modified
        if target.exists() and target.stat().st_mtime >= f.stat().st_mtime:
            continue

        shutil.copy2(str(f), str(target))
        imported.append(str(Path(repo_id) / rel).replace("\\", "/"))

    return imported


def _count_files(repo_id: str) -> int:
    """Count existing imported files for a repo."""
    target_base = BRAIN_NOTES / repo_id
    if not target_base.exists():
        return 0
    return sum(1 for f in target_base.rglob("*.md") if f.is_file())


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def list_repos() -> List[dict]:
    """Return list of connected repos with sync status."""
    data = _load_repos()
    repos = []
    for repo in data["repos"]:
        files_count = _count_files(repo["id"])
        repos.append({
            "id": repo["id"],
            "url": repo["url"],
            "branch": repo.get("branch", "main"),
            "last_sync": repo.get("last_sync"),
            "last_commit": repo.get("last_commit"),
            "pending_update": repo.get("pending_update", False),
            "files_count": files_count,
        })
    return repos


async def connect_repo(url: str, branch: str = "main", token: str = "",
                       repo_path: str = "") -> dict:
    """Connect a repo, clone it, and import files.

    Returns summary dict with repo_id and count.
    """
    repo_id = _gen_repo_id(url)
    data = _load_repos()

    # Check if already connected
    for existing in data["repos"]:
        if existing["id"] == repo_id:
            raise ValueError(f"Repo '{repo_id}' already connected — sync instead")

    # Clone
    clone_dir = TEMP_CLONE_DIR / repo_id
    try:
        _clone_repo(url, clone_dir, branch, token)
    except RuntimeError as e:
        raise RuntimeError(f"Failed to clone repo: {e}")

    # Import files
    imported = _import_files(repo_id, clone_dir, repo_path)

    # Get commit hash
    last_commit = _get_remote_commit(url, branch)

    # Save state
    entry = {
        "id": repo_id,
        "url": url,
        "branch": branch,
        "repo_path": repo_path,
        "last_sync": datetime.now().isoformat(),
        "last_commit": last_commit or "",
        "pending_update": False,
        "files": imported,
    }
    data["repos"].append(entry)
    _save_repos(data)

    # Cleanup clone
    if clone_dir.exists():
        _rmtree(clone_dir)

    # Rebuild index
    from backend.vector_store import rebuild_index
    index_count = await rebuild_index()
    logger.info(f"[RepoSync] Index rebuilt: {index_count} docs")

    return {
        "repo_id": repo_id,
        "files_imported": len(imported),
        "files_count": len(imported),
        "index_count": index_count,
    }


async def sync_repo(repo_id: str, token: str = "") -> dict:
    """Sync a connected repo: check remote, clone if changed, import updates.

    Returns summary dict with changes.
    """
    data = _load_repos()
    repo_entry = None
    for r in data["repos"]:
        if r["id"] == repo_id:
            repo_entry = r
            break
    if not repo_entry:
        raise ValueError(f"Repo '{repo_id}' not connected")

    url = repo_entry["url"]
    branch = repo_entry.get("branch", "main")
    repo_path = repo_entry.get("repo_path", "")
    stored_commit = repo_entry.get("last_commit", "")

    # Check remote for changes
    remote_commit = _get_remote_commit(url, branch)
    has_updates = remote_commit and remote_commit != stored_commit

    clone_dir = TEMP_CLONE_DIR / repo_id
    try:
        _clone_repo(url, clone_dir, branch, token)
    except RuntimeError as e:
        raise RuntimeError(f"Failed to clone repo: {e}")

    # Import new/changed files
    imported = _import_files(repo_id, clone_dir, repo_path)

    # Update state
    repo_entry["last_sync"] = datetime.now().isoformat()
    repo_entry["last_commit"] = remote_commit or stored_commit
    repo_entry["pending_update"] = False
    existing_files = set(repo_entry.get("files", []))
    repo_entry["files"] = list(existing_files | set(imported))
    _save_repos(data)

    # Cleanup
    if clone_dir.exists():
        _rmtree(clone_dir)

    # Rebuild index
    from backend.vector_store import rebuild_index
    index_count = await rebuild_index()

    return {
        "repo_id": repo_id,
        "has_updates": has_updates,
        "files_imported": len(imported),
        "files_count": _count_files(repo_id),
        "index_count": index_count,
    }


async def sync_all(token: str = "") -> List[dict]:
    """Sync all connected repos. Returns list of results."""
    data = _load_repos()
    results = []
    for repo in data["repos"]:
        try:
            result = await sync_repo(repo["id"], token)
            results.append(result)
        except Exception as e:
            results.append({"repo_id": repo["id"], "error": str(e)})
    return results


def disconnect_repo(repo_id: str, remove_files: bool = False) -> dict:
    """Disconnect a repo. Optionally remove imported files."""
    data = _load_repos()
    repo_entry = None
    for i, r in enumerate(data["repos"]):
        if r["id"] == repo_id:
            repo_entry = data["repos"].pop(i)
            break

    if not repo_entry:
        raise ValueError(f"Repo '{repo_id}' not connected")

    if remove_files:
        target_base = BRAIN_NOTES / repo_id
        if target_base.exists():
            _rmtree(target_base)

    _save_repos(data)
    return {"repo_id": repo_id, "files_removed": remove_files}


def check_updates() -> List[dict]:
    """Check remote for pending updates without cloning.

    Returns list of repos with pending_update flag.
    """
    data = _load_repos()
    updates = []
    for repo in data["repos"]:
        try:
            remote = _get_remote_commit(repo["url"], repo.get("branch", "main"))
            local = repo.get("last_commit", "")
            pending = bool(remote and remote != local)
            if pending:
                repo["pending_update"] = True
            updates.append({
                "id": repo["id"],
                "url": repo["url"],
                "pending_update": pending,
                "remote_commit": remote or "",
                "local_commit": local,
            })
        except Exception as e:
            updates.append({"id": repo["id"], "url": repo["url"], "error": str(e)})

    _save_repos(data)
    return updates
