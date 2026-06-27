import os
import re
import hashlib
import asyncio
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Optional

from backend.config import BRAIN_NOTES, BRAIN_CONNECTIONS
from backend.brain_manager import get_all_note_texts, write_note_raw
from backend.vector_store import embed_text, search, add_document, remove_document


_connector_running = False
_evolver_running = False
_last_connector_run: Optional[datetime] = None
_last_evolver_run: Optional[datetime] = None


def get_status() -> dict:
    return {
        "connector": "running" if _connector_running else "idle",
        "evolver": "running" if _evolver_running else "idle",
        "last_connector_run": _last_connector_run.isoformat() if _last_connector_run else None,
        "last_evolver_run": _last_evolver_run.isoformat() if _last_evolver_run else None,
    }


def _make_connection_filename(source: str, target: str) -> str:
    """Deterministic filename from a pair of note names."""
    pair = sorted([source, target])
    raw = f"{pair[0]}__{pair[1]}"
    h = hashlib.md5(raw.encode()).hexdigest()[:8]
    return f"conn_{h}.md"


async def _write_connection(source: str, target: str, similarity: float):
    """Write one connection file linking source<->target."""
    s_title = source.replace(".md", "").replace("-", " ").replace("_", " ").title()
    t_title = target.replace(".md", "").replace("-", " ").replace("_", " ").title()
    content = f"""# Conexion: {s_title} <-> {t_title}

> Conexion automatica generada por el Conector de Baul
> Similitud: {similarity:.4f}
> Fecha: {datetime.now().strftime("%Y-%m-%d %H:%M")}

---

[[{source.replace('.md', '')}]]

[[{target.replace('.md', '')}]]

---

*Conexion semantica detectada automaticamente.*
"""
    fname = _make_connection_filename(source, target)
    fpath = BRAIN_CONNECTIONS / fname
    fpath.write_text(content, encoding="utf-8")


async def _remove_stale_connections(active_pairs: set):
    """Delete connection files that are no longer relevant."""
    for f in BRAIN_CONNECTIONS.iterdir():
        if f.suffix.lower() == ".md" and f.name not in active_pairs:
            f.unlink(missing_ok=True)


async def run_connector():
    """El Conector - finds connections between notes and creates connection files."""
    global _connector_running, _last_connector_run

    if _connector_running:
        return {"status": "already_running"}

    _connector_running = True
    try:
        notes = await get_all_note_texts()
        if len(notes) < 2:
            return {"status": "not_enough_notes", "count": len(notes)}

        texts = [n["content"] for n in notes]
        filenames = [n["filename"] for n in notes]
        emb_results = await asyncio.gather(*[embed_text(t) for t in texts])
        embeddings = np.array(emb_results)

        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        normalized = embeddings / np.maximum(norms, 1e-10)
        sim_matrix = np.dot(normalized, normalized.T)

        threshold = 0.60
        merge_threshold = 0.98
        connections = []
        merges = []
        active_files = set()

        for i in range(len(notes)):
            for j in range(i + 1, len(notes)):
                sim = float(sim_matrix[i][j])
                if sim >= merge_threshold:
                    merges.append({
                        "source": filenames[i],
                        "target": filenames[j],
                        "similarity": round(sim, 4),
                    })
                elif sim > threshold:
                    connections.append({
                        "source": filenames[i],
                        "target": filenames[j],
                        "similarity": round(sim, 4),
                    })

        connections.sort(key=lambda x: x["similarity"], reverse=True)
        merges.sort(key=lambda x: x["similarity"], reverse=True)

        # Auto-merge notes with >= 0.98 similarity
        merged_count = 0
        merged_pairs = set()
        for m in merges:
            src, tgt = m["source"], m["target"]
            if src in merged_pairs or tgt in merged_pairs:
                continue
            src_path = BRAIN_NOTES / src
            tgt_path = BRAIN_NOTES / tgt
            if src_path.exists() and tgt_path.exists():
                src_text = src_path.read_text(encoding="utf-8")
                tgt_text = tgt_path.read_text(encoding="utf-8")
                merged = src_text + "\n\n---\n\n*Nota fusionada automaticamente*\n\n" + tgt_text
                await write_note_raw(src, merged)
                tgt_path.unlink(missing_ok=True)
                await remove_document(tgt)
                await add_document(src, merged)
                merged_pairs.add(src)
                merged_pairs.add(tgt)
                merged_count += 1
                print(f"[Baul] Fusion: {src} <-> {tgt} (sim: {m['similarity']})")

        # Keep only top-K connections per note to avoid graph clutter
        per_note = {}
        for conn in connections:
            per_note.setdefault(conn["source"], []).append(conn)
            per_note.setdefault(conn["target"], []).append(conn)
        best_pairs = set()
        for note, conns in per_note.items():
            conns.sort(key=lambda x: x["similarity"], reverse=True)
            for c in conns[:5]:
                pair = (c["source"], c["target"]) if c["source"] < c["target"] else (c["target"], c["source"])
                best_pairs.add(pair)

        # Write connection files (only top-K per note)
        for conn in connections:
            pair = (conn["source"], conn["target"]) if conn["source"] < conn["target"] else (conn["target"], conn["source"])
            if pair not in best_pairs:
                continue
            await _write_connection(conn["source"], conn["target"], conn["similarity"])
            active_files.add(_make_connection_filename(conn["source"], conn["target"]))

        # Remove stale connections
        await _remove_stale_connections(active_files)

        _last_connector_run = datetime.now()
        return {
            "status": "completed",
            "connections_found": len(connections),
            "notes_analyzed": len(notes),
            "merges_performed": merged_count,
            "top_connections": connections[:30],
        }

    finally:
        _connector_running = False


async def run_evolver():
    """El Evolucionador - analyzes patterns in notes. Returns data only, does NOT create files."""
    global _evolver_running, _last_evolver_run

    if _evolver_running:
        return {"status": "already_running"}

    _evolver_running = True
    try:
        notes = await get_all_note_texts()
        if not notes:
            return {"status": "no_notes"}

        all_tags = {}
        for note in notes:
            tags = re.findall(r"#(\w+)", note["content"])
            for tag in tags:
                if tag not in all_tags:
                    all_tags[tag] = []
                all_tags[tag].append(note["filename"])

        popular_tags = {t: f for t, f in all_tags.items() if len(f) >= 2}

        _last_evolver_run = datetime.now()
        return {
            "status": "completed",
            "tags_found": len(all_tags),
            "popular_tags": len(popular_tags),
            "top_tags": sorted(popular_tags.items(), key=lambda x: -len(x[1]))[:10],
        }

    finally:
        _evolver_running = False
