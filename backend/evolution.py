"""
evolution.py — Autonomous learning engine for Baul.

Handles:
  1. Knowledge consolidation from conversations
  2. Connection discovery between notes
  3. Draft note creation from web knowledge
  4. Periodic background evolution tasks
"""

import re
import json
import asyncio
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional
from collections import defaultdict

from backend.config import BRAIN_NOTES, BRAIN_CONNECTIONS, BRAIN_META

logger = logging.getLogger("baul.evolution")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SYSTEM_PREFIX = "_"
_EVOLUTION_META = BRAIN_META / "evolution.json"


def _load_meta() -> dict:
    if _EVOLUTION_META.exists():
        try:
            return json.loads(_EVOLUTION_META.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "last_consolidation": None,
        "last_connection_discovery": None,
        "conversation_count": 0,
        "draft_notes_created": [],
        "connections_discovered": [],
    }


def _save_meta(meta: dict):
    _EVOLUTION_META.parent.mkdir(parents=True, exist_ok=True)
    _EVOLUTION_META.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _get_all_note_contents() -> List[dict]:
    notes = []
    for f in sorted(BRAIN_NOTES.rglob("*.md")):
        if f.name.startswith(_SYSTEM_PREFIX):
            continue
        try:
            content = f.read_text(encoding="utf-8")
            rel = str(f.relative_to(BRAIN_NOTES)).replace("\\", "/")
            notes.append({"filename": rel, "content": content, "path": f})
        except Exception:
            continue
    return notes


# ---------------------------------------------------------------------------
# 1. Knowledge Consolidation
# ---------------------------------------------------------------------------

_CONSOLIDATION_PROMPT = """Eres un asistente que extrae conocimiento valioso de conversaciones.
Analiza el siguiente intercambio y decide si contiene informacion que valga la pena
guardar como una nota en el Baul del usuario.

Reglas:
- SOLO extrae informacion que sea factual, nueva y util
- NO extraes saludos, opiniones triviales ni conversacion casual
- Si hay informacion valiosa, genera un titulo corto (max 60 chars)
- Si no hay informacion valiosa, responde SOLO con "NO_ACTION"

Formato de respuesta si hay informacion valiosa:
TITULO: <titulo>
CONTENIDO: <contenido de la nota>

Conversacion:
"""


def _extract_knowledge_from_conversation(conversation_text: str) -> Optional[dict]:
    """Extract note-worthy knowledge from a conversation using keyword heuristics."""
    lines = conversation_text.split("\n")
    useful_lines = []
    keywords = [
        "es ", "son ", "esta ", "estan ", "tiene ", "tienen ", "funciona",
        "significa", "consiste", "define", "ejemplo", "importante",
        "clave", "pasos", "proceso", "tutorial", "guia", "como ",
        "diferencia", "ventaja", "desventaja", "caracteristica",
        "historia", "origen", "causa", "consecuencia", "motivo",
        "is ", "are ", "has ", "have ", "means ", "defined as",
        "example", "important", "steps", "process", "tutorial",
        "guide", "how to", "difference", "advantage", "feature",
        "history", "origin", "cause", "reason",
    ]

    for line in lines:
        stripped = line.strip()
        if any(kw in stripped.lower() for kw in keywords) and len(stripped) > 40:
            useful_lines.append(stripped)

    if len(useful_lines) >= 2:
        content = "\n".join(useful_lines)
        # Extract a title from the first substantive line
        first_line = useful_lines[0]
        title_match = re.match(r"^(.{10,60})[.:]", first_line)
        title = title_match.group(1) if title_match else first_line[:50].strip()
        return {
            "title": title,
            "content": content[:2000],
            "source": "conversation",
        }
    return None


# ---------------------------------------------------------------------------
# 2. Connection Discovery
# ---------------------------------------------------------------------------

def _discover_note_connections() -> List[dict]:
    """Find related notes by keyword overlap and cross-references."""
    notes = _get_all_note_contents()
    if len(notes) < 2:
        return []

    connections = []
    # Build keyword index per note
    note_keywords = {}
    for note in notes:
        words = set(
            w.lower() for w in re.findall(r"\b[a-zA-Z\u00f1\u00e1-\u00fa]{4,}\b", note["content"])
            if w.lower() not in {
                "que", "para", "como", "mas", "pero", "con", "por", "del",
                "las", "los", "una", "eso", "the", "and", "for", "that",
                "this", "with", "from", "have", "are", "was",
            }
        )
        note_keywords[note["filename"]] = words

    filenames = list(note_keywords.keys())
    for i in range(len(filenames)):
        for j in range(i + 1, len(filenames)):
            a, b = filenames[i], filenames[j]
            common = note_keywords[a] & note_keywords[b]
            if len(common) >= 3:
                connections.append({
                    "source": a,
                    "target": b,
                    "common_terms": list(common),
                    "strength": round(len(common) / max(len(note_keywords[a] | note_keywords[b]), 1), 3),
                })

    connections.sort(key=lambda c: c["strength"], reverse=True)
    return connections[:20]


async def save_connections():
    """Write discovered connections to a JSON file for the graph."""
    meta = _load_meta()
    connections = _discover_note_connections()

    conn_path = BRAIN_CONNECTIONS / "_discovered.json"
    conn_path.parent.mkdir(parents=True, exist_ok=True)
    conn_path.write_text(
        json.dumps(connections, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    meta["connections_discovered"] = [
        f"{c['source']} <-> {c['target']}" for c in connections[:10]
    ]
    meta["last_connection_discovery"] = datetime.now().isoformat()
    _save_meta(meta)

    logger.info(f"[Evolution] Discovered {len(connections)} note connections")
    return connections


# ---------------------------------------------------------------------------
# 3. Draft Note Creation
# ---------------------------------------------------------------------------

async def create_draft_note(title: str, content: str, source: str = "auto") -> Optional[str]:
    """Create a draft note in the Baul with _draft prefix."""
    safe_title = re.sub(r"[^a-zA-Z0-9\u00f1\u00e1-\u00fa\s-]", "", title).strip().lower()
    safe_title = re.sub(r"\s+", "-", safe_title)[:60]
    filename = f"_draft-{safe_title}.md"
    path = BRAIN_NOTES / filename

    if path.exists():
        logger.info(f"[Evolution] Draft note already exists: {filename}")
        return None

    full_content = f"# {title}\n\n*Nota generada autonomicamente el {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n*Fuente: {source}*\n\n{content}"
    path.write_text(full_content, encoding="utf-8")

    meta = _load_meta()
    meta["draft_notes_created"].append(filename)
    _save_meta(meta)

    logger.info(f"[Evolution] Created draft note: {filename}")
    return filename


async def consolidate_from_conversation(conversation_pairs: list) -> Optional[str]:
    """Process conversation history and create draft notes from useful info."""
    if not conversation_pairs:
        return None

    # Track conversation count
    meta = _load_meta()
    meta["conversation_count"] = meta.get("conversation_count", 0) + 1
    _save_meta(meta)

    text = "\n".join(
        f"{'Usuario' if p.get('role') == 'user' else 'EAgis'}: {p.get('content', '')}"
        for p in conversation_pairs[-6:]
    )

    knowledge = _extract_knowledge_from_conversation(text)
    if knowledge:
        filename = await create_draft_note(
            knowledge["title"], knowledge["content"],
            source=f"conversation_{datetime.now().strftime('%Y%m%d')}",
        )
        return filename
    return None


# ---------------------------------------------------------------------------
# 4. Periodic Background Tasks
# ---------------------------------------------------------------------------

_RUNNING = False


async def background_evolution_loop(interval_seconds: int = 1800):
    """Run evolution tasks periodically in the background."""
    global _RUNNING
    if _RUNNING:
        return
    _RUNNING = True

    logger.info(f"[Evolution] Background loop started (interval={interval_seconds}s)")

    while _RUNNING:
        try:
            meta = _load_meta()
            now = datetime.now()

            # Run consolidation every interval
            last_cons = meta.get("last_consolidation")
            if not last_cons or (now - datetime.fromisoformat(last_cons)) > timedelta(seconds=interval_seconds):
                await save_connections()
                meta["last_consolidation"] = now.isoformat()
                _save_meta(meta)

        except Exception as e:
            logger.error(f"[Evolution] Background error: {e}")

        await asyncio.sleep(interval_seconds)


def stop_background_evolution():
    global _RUNNING
    _RUNNING = False


# ---------------------------------------------------------------------------
# API-friendly summary
# ---------------------------------------------------------------------------

def get_evolution_stats() -> dict:
    meta = _load_meta()
    return {
        "last_consolidation": meta.get("last_consolidation"),
        "last_connection_discovery": meta.get("last_connection_discovery"),
        "conversation_count": meta.get("conversation_count", 0),
        "draft_notes_count": len(meta.get("draft_notes_created", [])),
        "connections_count": len(meta.get("connections_discovered", [])),
    }
