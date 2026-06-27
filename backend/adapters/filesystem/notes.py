"""FileSystemNoteRepository — reads/writes notes as .md files."""
import os
import re
from typing import Optional
from pathlib import Path

from backend.domain.models import Note
from backend.domain.exceptions import NoteNotFoundError
from backend.ports.repositories import NoteRepository
from backend.infrastructure.logger import get_logger

logger = get_logger("adapters.fs.notes")


class FileSystemNoteRepository(NoteRepository):
    """Stores notes as individual .md files in brain/baul/ and knowledge dirs."""

    def __init__(self, brain_dir: Path, knowledge_dirs: dict[str, Path]):
        self._brain_dir = brain_dir
        self._knowledge_dirs = knowledge_dirs
        self._lock = None  # lazy init in async context

    async def _get_lock(self):
        if self._lock is None:
            import asyncio
            self._lock = asyncio.Lock()
        return self._lock

    async def _resolve_path(self, filename: str) -> Optional[Path]:
        """Find a note file across brain and knowledge directories."""
        # Direct brain path
        for base in [self._brain_dir / "baul" / "notes", self._brain_dir / "inbox"]:
            path = base / filename
            if path.exists():
                return path
        # Knowledge library dirs
        for cat_name, cat_dir in self._knowledge_dirs.items():
            path = cat_dir / filename
            if path.exists():
                return path
        return None

    async def get(self, filename: str) -> Optional[Note]:
        async with await self._get_lock():
            try:
                path = await self._resolve_path(filename)
                if not path:
                    return None
                content = path.read_text(encoding="utf-8", errors="replace")
                title = path.stem.replace("-", " ").title()
                tags = re.findall(r"tags:\s*\[([^\]]+)\]", content)
                tag_list = [t.strip() for t in tags[0].split(",")] if tags else []
                return Note(
                    title=title,
                    content=content,
                    tags=tag_list,
                    folder=path.parent.name,
                    filename=filename,
                )
            except Exception as e:
                logger.error("Failed to read note '%s': %s", filename, e)
                return None

    async def save(self, note: Note) -> str:
        async with await self._get_lock():
            try:
                notes_dir = self._brain_dir / "baul" / "notes"
                notes_dir.mkdir(parents=True, exist_ok=True)
                filename = note.filename or f"{note.title.lower().replace(' ', '-')[:60]}.md"
                path = notes_dir / filename
                path.write_text(note.content, encoding="utf-8")
                logger.info("Saved note: %s", filename)
                return filename
            except Exception as e:
                logger.error("Failed to save note '%s': %s", note.title, e)
                raise

    async def delete(self, filename: str) -> bool:
        async with await self._get_lock():
            try:
                path = await self._resolve_path(filename)
                if path:
                    path.unlink()
                    logger.info("Deleted note: %s", filename)
                    return True
                return False
            except Exception as e:
                logger.error("Failed to delete note '%s': %s", filename, e)
                return False

    async def list_all(self, folder: str = "") -> list[Note]:
        async with await self._get_lock():
            notes = []
            base_path = self._brain_dir / "baul" / "notes"
            if not base_path.exists():
                return notes
            pattern = "*.md"
            for f in sorted(base_path.rglob(pattern)):
                if f.name.startswith("_"):
                    continue
                try:
                    content = f.read_text(encoding="utf-8", errors="replace")[:200]
                    notes.append(Note(
                        title=f.stem.replace("-", " ").title(),
                        content=content,
                        filename=str(f.relative_to(self._brain_dir / "baul" / "notes")),
                        folder=f.parent.name if f.parent.name != "notes" else "",
                    ))
                except Exception as e:
                    logger.warning("Skipping unreadable note %s: %s", f.name, e)
            return notes

    async def search_by_content(self, query: str) -> list[Note]:
        """Brute-force content search across all notes."""
        async with await self._get_lock():
            results = []
            q = query.lower()
            base = self._brain_dir / "baul" / "notes"
            if not base.exists():
                return results
            for f in base.rglob("*.md"):
                if f.name.startswith("_"):
                    continue
                try:
                    content = f.read_text(encoding="utf-8", errors="replace")
                    if q in content.lower():
                        results.append(Note(
                            title=f.stem.replace("-", " ").title(),
                            content=content[:500],
                            filename=str(f.relative_to(base)),
                        ))
                except Exception:
                    continue
            return results
