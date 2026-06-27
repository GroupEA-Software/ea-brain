"""
graph.py — Knowledge graph for the unified Baul brain.

Includes both brain/baul/ notes (user notes) and __conocimiento__/
notes (knowledge library 01-07). Builds nodes and edges from wikilinks
and auto-generated connections across ALL sources.
"""

import re
import time
import asyncio
from fastapi import APIRouter, Query
from backend.brain_manager import list_notes, get_note, get_connections_files, \
    list_knowledge, get_knowledge_note

router = APIRouter(prefix="/api")


def _norm(name: str) -> str:
    return name.replace(".md", "").lower().replace(" ", "-").replace("/", "-").replace("\\", "-")


def _build_note_map(notes: list) -> dict:
    """Build slug->filename map for wikilink resolution."""
    slug_map = {}
    for n in notes:
        slug = _norm(n["filename"])
        title = n.get("title", "").lower()
        slug_map[slug] = n["filename"]
        if title:
            slug_map[title] = n["filename"]
        # Also index by stem for fuzzy matching
        stem = n["filename"].split("/")[-1].replace(".md", "").lower()
        slug_map[stem] = n["filename"]
    return slug_map


# Simple cache with 30s TTL
_graph_cache = {"data": None, "timestamp": 0.0, "ttl": 30}


@router.get("/brain/graph")
async def api_brain_graph(
    limit: int = Query(500, ge=10, le=2000),
    min_weight: float = Query(0.15, ge=0.0, le=1.0),
):
    """Return knowledge graph nodes and edges with caching, concurrency, and limits."""
    # ── Cache check: 30s TTL ──
    now = time.time()
    if _graph_cache["data"] and now - _graph_cache["timestamp"] < _graph_cache["ttl"]:
        return _graph_cache["data"]

    # ── 1. Load baul notes concurrently ──
    baul_notes = await list_notes()
    tasks = [get_note(n["filename"]) for n in baul_notes]
    notes_data = await asyncio.gather(*tasks)

    all_content = {}
    for n, note_data in zip(baul_notes, notes_data):
        if note_data:
            all_content[n["filename"]] = note_data["content"]

    slug_map = _build_note_map(baul_notes)

    # ── 2. Load knowledge notes (concurrently, all of them) ──
    knowledge_cats = await list_knowledge()
    knowledge_files = []
    for cat in knowledge_cats:
        for kf in cat["files"]:
            knowledge_files.append((cat, kf))
    # No artificial limit — user controls via ?limit= param

    k_tasks = [get_knowledge_note(kf["filename"]) for _, kf in knowledge_files]
    k_notes_data = await asyncio.gather(*k_tasks)

    knowledge_nodes = []
    for (cat, kf), knote in zip(knowledge_files, k_notes_data):
        if not knote:
            continue
        all_content[kf["filename"]] = knote["content"]
        slug_map[_norm(kf["filename"])] = kf["filename"]
        slug_map[kf["title"].lower()] = kf["filename"]
        stem = kf["filename"].split("/")[-1].replace(".md", "").lower()
        slug_map[stem] = kf["filename"]

        knowledge_nodes.append({
            "id": _norm(kf["filename"]),
            "label": kf["title"],
            "folder": cat["name"],
            "group": "knowledge",
            "size": max(2, min(20, (max(kf.get("size", 0), 100) / 300))),
        })

    # ── 3. Build nodes ──
    nodes = []
    for n in baul_notes:
        nodes.append({
            "id": _norm(n["filename"]),
            "label": n["title"],
            "folder": n.get("folder", ""),
            "group": "note",
            "size": max(2, min(20, (n.get("size", 0) / 200))),
        })
    nodes.extend(knowledge_nodes)

    # ── 4. Build edges from wikilinks ──
    edges = []
    edge_set = set()

    for filename, content in all_content.items():
        source_id = _norm(filename)
        links = re.findall(r'\[\[([^\]]+)\]\]', content)
        for link in links:
            target = slug_map.get(link.lower().replace(" ", "-"))
            if not target:
                target = slug_map.get(link.lower())
            if not target:
                # Try matching by any key containing the link text
                for key, val in slug_map.items():
                    if link.lower() in key:
                        target = val
                        break
            if target and target != filename:
                target_id = _norm(target)
                edge_key = tuple(sorted([source_id, target_id]))
                if edge_key not in edge_set:
                    edge_set.add(edge_key)
                    edges.append({"source": source_id, "target": target_id, "weight": 1.0})

    # ── 5. Build edges from auto-connections (filter by min_weight) ──
    conn_files = await get_connections_files()
    for conn_file in conn_files:
        content = conn_file["content"]
        sim_match = re.search(r'Similitud:\s*([\d.]+)', content)
        weight = float(sim_match.group(1)) if sim_match else 0.6
        if weight < min_weight:
            continue
        links = re.findall(r'\[\[([^\]]+)\]\]', content)
        for i in range(0, len(links) - 1, 2):
            if i + 1 < len(links):
                s = _norm(links[i])
                t = _norm(links[i + 1])
                if s != t:
                    edge_key = tuple(sorted([s, t]))
                    if edge_key not in edge_set:
                        edge_set.add(edge_key)
                        edges.append({"source": s, "target": t, "weight": weight})

    # ── 6. Enforce node limit: keep top N by connected edge count ──
    if len(nodes) > limit:
        edge_count = {}
        for e in edges:
            edge_count[e["source"]] = edge_count.get(e["source"], 0) + 1
            edge_count[e["target"]] = edge_count.get(e["target"], 0) + 1
        nodes.sort(key=lambda n: edge_count.get(n["id"], 0), reverse=True)
        keep_ids = set(n["id"] for n in nodes[:limit])
        nodes = [n for n in nodes if n["id"] in keep_ids]
        edges = [e for e in edges if e["source"] in keep_ids and e["target"] in keep_ids]

    # ── 7. Cache and return ──
    result = {"nodes": nodes, "edges": edges}
    _graph_cache["data"] = result
    _graph_cache["timestamp"] = now
    return result


@router.get("/wikilinks/{filename:path}")
async def api_wikilinks(filename: str):
    """Get wikilinks from a note, resolving against both baul and knowledge notes."""
    # Try baul note first
    note = await get_note(filename)
    is_knowledge = False
    if not note:
        note = await get_knowledge_note(filename)
        is_knowledge = bool(note)

    if not note:
        return {"error": "Nota no encontrada"}, 404

    content = note["content"]
    links = re.findall(r'\[\[([^\]]+)\]\]', content)

    # Build unified map from both sources
    baul_notes = await list_notes()
    knowledge_cats = await list_knowledge()

    note_map = {}
    for n in baul_notes:
        slug = _norm(n["filename"])
        title = n["title"].lower()
        note_map[slug] = n["filename"]
        note_map[title] = n["filename"]

    for cat in knowledge_cats:
        for kf in cat["files"]:
            slug = _norm(kf["filename"])
            title = kf["title"].lower()
            note_map[slug] = kf["filename"]
            note_map[title] = kf["filename"]

    resolved = []
    for link in links:
        target = note_map.get(link.lower().replace(" ", "-"))
        if not target:
            target = note_map.get(link.lower())
        if not target:
            for key, val in note_map.items():
                if link.lower() in key:
                    target = val
                    break
        if target:
            resolved.append({"wikilink": link, "filename": target, "exists": True})
        else:
            resolved.append({"wikilink": link, "filename": None, "exists": False})

    return {"source": filename, "links": resolved, "is_knowledge": is_knowledge}


@router.get("/backlinks/{filename:path}")
async def api_backlinks(filename: str):
    """Get backlinks from ALL notes (baul + knowledge) pointing to this one."""
    target_slug = _norm(filename)
    target_title = filename.replace(".md", "").replace("-", " ").lower()
    target_stem = filename.split("/")[-1].replace(".md", "").lower()

    # Get all baul notes
    baul_notes = await list_notes()
    backlinks = []

    # Search baul notes
    for n in baul_notes:
        if n["filename"] == filename:
            continue
        note = await get_note(n["filename"])
        if note:
            content_lower = note["content"].lower()
            if ("[[" + target_slug + "]]" in content_lower or
                "[[" + target_title + "]]" in content_lower or
                "[[" + target_stem + "]]" in content_lower):
                backlinks.append({"filename": n["filename"], "title": n["title"]})

    # Search knowledge notes
    knowledge_cats = await list_knowledge()
    for cat in knowledge_cats:
        for kf in cat["files"]:
            if kf["filename"] == filename:
                continue
            knote = await get_knowledge_note(kf["filename"])
            if knote:
                content_lower = knote["content"].lower()
                if ("[[" + target_slug + "]]" in content_lower or
                    "[[" + target_title + "]]" in content_lower or
                    "[[" + target_stem + "]]" in content_lower):
                    backlinks.append({"filename": kf["filename"], "title": kf["title"]})

    return {"filename": filename, "backlinks": backlinks}
