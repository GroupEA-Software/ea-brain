"""
graph.py — Knowledge graph for the unified Baul brain.

Includes both brain/baul/ notes (user notes) and __conocimiento__/
notes (knowledge library 01-07). Builds nodes and edges from wikilinks
and auto-generated connections across ALL sources.
"""

import re
from fastapi import APIRouter
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


@router.get("/brain/graph")
async def api_brain_graph():
    # ── 1. Load baul notes ──
    baul_notes = await list_notes()
    all_content = {}
    slug_map = {}

    for n in baul_notes:
        note = await get_note(n["filename"])
        if note:
            all_content[n["filename"]] = note["content"]

    slug_map = _build_note_map(baul_notes)

    # ── 2. Load knowledge notes ──
    knowledge_cats = await list_knowledge()
    knowledge_nodes = []
    for cat in knowledge_cats:
        for kf in cat["files"]:
            knote = await get_knowledge_note(kf["filename"])
            if knote:
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

    # ── 5. Build edges from auto-connections ──
    conn_files = await get_connections_files()
    for conn_file in conn_files:
        content = conn_file["content"]
        sim_match = re.search(r'Similitud:\s*([\d.]+)', content)
        weight = float(sim_match.group(1)) if sim_match else 0.6
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

    return {"nodes": nodes, "edges": edges}


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
