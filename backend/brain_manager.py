import os
import re
import json
import zipfile
import io
from pathlib import Path
from datetime import datetime
from typing import List, Optional
import aiofiles
from backend.config import BRAIN_NOTES, BRAIN_INBOX, BRAIN_CONNECTIONS, BRAIN_META, KNOWLEDGE_DIRS


SYSTEM_PREFIX = "_"


def _is_system_note(filename: str) -> bool:
    return filename.startswith(SYSTEM_PREFIX)


def _slugify(title: str) -> str:
    slug = title.lower().strip()
    slug = re.sub(r"[^a-z0-9\u00f1\u00e1-\u00fa\s\/-]", "", slug)
    slug = re.sub(r"[\s-]+", "-", slug)
    slug = re.sub(r"\/+", "/", slug)
    return slug[:200]


def _extract_title(content: str) -> str:
    for line in content.split("\n"):
        if line.startswith("# "):
            return line[2:].strip()
    return "Untitled"


def _extract_tags(content: str) -> List[str]:
    return re.findall(r"#(\w+)", content)


async def list_notes() -> List[dict]:
    notes = []
    for f in sorted(BRAIN_NOTES.rglob("*.md"), key=lambda p: str(p.relative_to(BRAIN_NOTES)).lower()):
        if _is_system_note(f.name) or ".agent" in str(f):
            continue
        rel = f.relative_to(BRAIN_NOTES)
        folder = str(rel.parent).replace("\\", "/") if rel.parent != Path(".") else ""
        notes.append({
            "filename": str(rel).replace("\\", "/"),
            "title": f.stem.replace("-", " ").replace("_", " ").title(),
            "folder": folder,
            "modified": datetime.fromtimestamp(os.path.getmtime(f)).isoformat(),
            "created": datetime.fromtimestamp(os.path.getctime(f)).isoformat(),
            "size": f.stat().st_size,
        })
    return notes


async def get_note(filename: str) -> Optional[dict]:
    path = BRAIN_NOTES / filename
    if not path.exists():
        path = BRAIN_NOTES / f"{filename}.md"
    if not path.exists():
        # Try finding by slug
        for f in BRAIN_NOTES.rglob("*.md"):
            if f.stem == filename.replace(".md", ""):
                path = f
                break
    if not path.exists():
        return None
    async with aiofiles.open(str(path), encoding="utf-8") as f:
        text = await f.read()
    title = _extract_title(text)
    tags = _extract_tags(text)
    rel = path.relative_to(BRAIN_NOTES)
    return {
        "filename": str(rel).replace("\\", "/"),
        "title": title,
        "content": text,
        "tags": tags,
        "modified": datetime.fromtimestamp(os.path.getmtime(path)).isoformat(),
    }


async def create_note(title: str, content: str = "", tags: List[str] = None, folder: str = "") -> dict:
    slug = _slugify(title)
    filename = f"{slug}.md"
    if folder:
        filename = f"{folder}/{filename}"
    path = BRAIN_NOTES / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    tags_str = " ".join(f"#{t}" for t in (tags or []))
    header = f"# {title}\n\n{tags_str}\n\n" if tags_str else f"# {title}\n\n"
    full = header + content
    async with aiofiles.open(str(path), "w", encoding="utf-8") as f:
        await f.write(full)
    return {"filename": filename, "title": title, "content": full}


async def update_note(filename: str, content: str) -> dict:
    path = BRAIN_NOTES / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(str(path), "w", encoding="utf-8") as f:
        await f.write(content)
    title = _extract_title(content)
    return {"filename": filename, "title": title, "content": content}


async def move_note(filename: str, target_folder: str) -> dict:
    path = BRAIN_NOTES / filename
    if not path.exists():
        return {"error": "Nota no encontrada"}
    content = path.read_text(encoding="utf-8")
    new_name = path.name
    if target_folder:
        new_path = BRAIN_NOTES / target_folder / new_name
    else:
        new_path = BRAIN_NOTES / new_name
    new_path.parent.mkdir(parents=True, exist_ok=True)
    path.unlink()
    new_path.write_text(content, encoding="utf-8")
    new_rel = str(new_path.relative_to(BRAIN_NOTES)).replace("\\", "/")

    from backend.vector_store import remove_document, add_document
    await remove_document(filename)
    await add_document(new_rel, content)

    return {"filename": new_rel, "folder": target_folder}


async def delete_note(filename: str) -> bool:
    path = BRAIN_NOTES / filename
    if path.exists():
        path.unlink()
        return True
    return False


async def create_folder(folder_path: str) -> dict:
    path = BRAIN_NOTES / folder_path
    path.mkdir(parents=True, exist_ok=True)
    return {"folder": folder_path, "created": True}


async def list_folders() -> List[str]:
    folders = set()
    for f in BRAIN_NOTES.rglob("*.md"):
        if _is_system_note(f.name):
            continue
        rel = f.relative_to(BRAIN_NOTES)
        parent = str(rel.parent).replace("\\", "/")
        if parent != "." and not parent.startswith(".agent"):
            folders.add(parent)
    return sorted(folders)


async def write_note_raw(filename: str, content: str):
    path = BRAIN_NOTES / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(str(path), "w", encoding="utf-8") as f:
        await f.write(content)


async def get_inbox_files() -> List[dict]:
    AUDIO_EXT = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".wma", ".aac", ".webm"}
    files = []
    for f in BRAIN_INBOX.iterdir():
        if f.is_file():
            ext = f.suffix.lower()
            file_type = "audio" if ext in AUDIO_EXT else "document"
            files.append({
                "filename": f.name,
                "size": f.stat().st_size,
                "ext": ext,
                "type": file_type,
                "modified": datetime.fromtimestamp(os.path.getmtime(f)).isoformat(),
            })
    return files


async def get_all_note_texts(include_knowledge: bool = True) -> List[dict]:
    texts = []
    for f in BRAIN_NOTES.rglob("*.md"):
        if _is_system_note(f.name):
            continue
        async with aiofiles.open(str(f), encoding="utf-8") as fh:
            text = await fh.read()
        rel = f.relative_to(BRAIN_NOTES)
        texts.append({"filename": str(rel).replace("\\", "/"), "content": text})

    if include_knowledge:
        for category_name, category_dir in KNOWLEDGE_DIRS.items():
            if not category_dir.is_dir():
                continue
            for f in sorted(category_dir.rglob("*.md")):
                if f.name.startswith("_"):
                    continue
                try:
                    async with aiofiles.open(str(f), encoding="utf-8") as fh:
                        text = await fh.read()
                    rel = f.relative_to(category_dir)
                    escaped_rel = str(rel).replace("\\", "/")
                    filename = f"__conocimiento__/{category_name}/{escaped_rel}"
                    texts.append({"filename": filename, "content": text})
                except Exception:
                    continue

    return texts


async def list_knowledge() -> List[dict]:
    """List knowledge files organized by category from 01-07 directories."""
    categories = []
    for category_name, category_dir in sorted(KNOWLEDGE_DIRS.items()):
        if not category_dir.is_dir():
            continue
        files = []
        for f in sorted(category_dir.rglob("*.md")):
            if f.name.startswith("_"):
                continue
            rel = f.relative_to(category_dir)
            escaped_rel = str(rel).replace("\\", "/")
            files.append({
                "filename": f"__conocimiento__/{category_name}/{escaped_rel}",
                "title": f.stem.replace("-", " ").replace("_", " ").title(),
                "path": escaped_rel,
                "size": f.stat().st_size,
                "modified": datetime.fromtimestamp(os.path.getmtime(f)).isoformat(),
            })
        categories.append({
            "name": category_name,
            "directory": str(category_dir.relative_to(category_dir.parent.parent)).replace("\\", "/") if category_dir.parent.parent else str(category_dir),
            "files": files,
            "total": len(files),
        })
    return categories


async def get_knowledge_note(filename: str) -> Optional[dict]:
    """Get the full content of a knowledge note by its virtual filename."""
    # Format: __conocimiento__/<Category>/<path>
    if not filename.startswith("__conocimiento__/"):
        return None

    parts = filename.replace("\\", "/").split("/", 2)
    if len(parts) < 3:
        return None

    # Map category name back to directory
    category_name = parts[1]
    file_path = parts[2]
    
    # Find matching directory
    for cat, cat_dir in KNOWLEDGE_DIRS.items():
        # Normalize for comparison
        if _norm_cat(cat) == _norm_cat(category_name):
            target = cat_dir / file_path
            if target.exists():
                async with aiofiles.open(str(target), encoding="utf-8") as fh:
                    text = await fh.read()
                title = _extract_title(text)
                tags = _extract_tags(text)
                return {
                    "filename": filename,
                    "title": title or target.stem.replace("-", " ").replace("_", " ").title(),
                    "content": text,
                    "tags": tags,
                    "category": cat,
                    "modified": datetime.fromtimestamp(os.path.getmtime(target)).isoformat(),
                    "readonly": True,
                }
    return None


def _norm_cat(name: str) -> str:
    return name.lower().strip().replace(" ", "").replace("-", "").replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")


async def get_connections_files() -> List[dict]:
    files = []
    for f in BRAIN_CONNECTIONS.glob("*.md"):
        async with aiofiles.open(str(f), encoding="utf-8") as fh:
            text = await fh.read()
        files.append({"filename": f.name, "content": text})
    return files


async def export_note_md(filename: str) -> Optional[str]:
    path = BRAIN_NOTES / filename
    if not path.exists():
        return None
    async with aiofiles.open(str(path), encoding="utf-8") as f:
        return await f.read()


_EXPORT_CSS = """
@page {
  margin: 25mm 20mm;
  @bottom-center {
    content: counter(page);
    font-size: 9pt;
    color: #999;
  }
}
body {
  font-family: 'Georgia', 'Times New Roman', serif;
  max-width: 700px;
  margin: 0 auto;
  padding: 0;
  line-height: 1.8;
  color: #1a1a1a;
  font-size: 11pt;
}
h1 {
  font-size: 26pt;
  font-weight: 700;
  border-bottom: 1px solid #1a1a1a;
  padding-bottom: 6px;
  margin: 32px 0 16px;
  letter-spacing: -0.3px;
}
h2 { font-size: 18pt; margin: 28px 0 10px; color: #2a2a2a; }
h3 { font-size: 14pt; margin: 22px 0 8px; color: #444; }
p { margin-bottom: 10px; text-align: justify; }
code {
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
  font-size: 9.5pt;
  background: #f5f5f5;
  padding: 2px 6px;
  border-radius: 3px;
  color: #d63384;
}
pre {
  background: #f8f8f8;
  border: 1px solid #e0e0e0;
  padding: 14px 16px;
  border-radius: 6px;
  overflow-x: auto;
  font-size: 9pt;
  line-height: 1.5;
}
pre code { background: none; padding: 0; color: inherit; }
table {
  border-collapse: collapse;
  width: 100%;
  margin: 14px 0;
  font-size: 10pt;
}
th, td {
  border: 1px solid #ccc;
  padding: 8px 10px;
  text-align: left;
}
th { background: #f0f0f0; font-weight: 600; }
blockquote {
  border-left: 3px solid #888;
  margin: 12px 0;
  padding: 4px 0 4px 18px;
  color: #555;
  font-style: italic;
}
ul, ol { padding-left: 22px; margin-bottom: 10px; }
li { margin-bottom: 4px; }
hr { border: none; border-top: 1px solid #ddd; margin: 24px 0; }
a { color: #2563eb; text-decoration: none; }
img { max-width: 100%; height: auto; border-radius: 4px; }
.footer {
  margin-top: 40px;
  padding-top: 12px;
  border-top: 1px solid #ddd;
  font-size: 8pt;
  color: #999;
  text-align: center;
}
@media print {
  body { font-size: 10pt; }
  h1 { font-size: 22pt; }
  h2 { font-size: 16pt; }
}
"""


async def export_note_pdf(filename: str) -> Optional[bytes]:
    """Convert a note to PDF. Returns PDF bytes or None."""
    path = BRAIN_NOTES / filename
    if not path.exists():
        return None
    async with aiofiles.open(str(path), encoding="utf-8") as f:
        md_text = await f.read()
    try:
        import markdown
        from datetime import datetime
        html_body = markdown.markdown(md_text, extensions=["fenced_code", "tables"])
        title = _extract_title(md_text)
        footer = f'<div class="footer">Generado por Baul &mdash; {datetime.now().strftime("%Y-%m-%d %H:%M")}</div>'
        styled = f"""<!DOCTYPE html><html lang="es"><head><meta charset="utf-8"><title>{title}</title><style>{_EXPORT_CSS}</style></head><body>{html_body}{footer}</body></html>"""
        try:
            from weasyprint import HTML
            pdf_bytes = HTML(string=styled).write_pdf()
            return pdf_bytes
        except ImportError:
            return None
    except ImportError:
        return None


async def export_note_html(filename: str) -> Optional[str]:
    """Convert a note to styled HTML (for browser display / print-to-PDF)."""
    path = BRAIN_NOTES / filename
    if not path.exists():
        return None
    async with aiofiles.open(str(path), encoding="utf-8") as f:
        md_text = await f.read()
    try:
        import markdown
        from datetime import datetime
        html_body = markdown.markdown(md_text, extensions=["fenced_code", "tables"])
        title = _extract_title(md_text)
        footer = f'<div class="footer">Generado por Baul &mdash; {datetime.now().strftime("%Y-%m-%d %H:%M")}</div>'
        styled = f"""<!DOCTYPE html><html lang="es"><head><meta charset="utf-8"><title>{title}</title><style>{_EXPORT_CSS}</style></head><body>{html_body}{footer}</body></html>"""
        return styled
    except ImportError:
        return md_text


async def export_vault_zip() -> Optional[bytes]:
    """Export all notes and connections as a ZIP file."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(BRAIN_NOTES.rglob("*.md")):
            if _is_system_note(f.name):
                continue
            rel = f.relative_to(BRAIN_NOTES)
            zf.write(str(f), str(rel).replace("\\", "/"))
        for f in sorted(BRAIN_CONNECTIONS.glob("*.md")):
            rel = f.relative_to(BRAIN_CONNECTIONS.parent)
            zf.write(str(f), str(rel))
        # Include .env if it exists
        env_path = BRAIN_NOTES.parent.parent / ".env"
        if env_path.exists():
            zf.write(str(env_path), "_config/env.txt")
    buf.seek(0)
    return buf.getvalue()
