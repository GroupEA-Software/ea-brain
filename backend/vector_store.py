import os
import json
import asyncio
import numpy as np
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from backend.config import BRAIN_META, EMBEDDING_MODEL, VECTOR_DIM

INDEX_PATH = BRAIN_META / "vectors.index"
META_PATH = BRAIN_META / "documents.json"

_model = None
_index = None
_documents: list = []
_executor = ThreadPoolExecutor(max_workers=1)


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def _get_index():
    global _index
    if _index is None:
        import faiss
        if INDEX_PATH.exists():
            _index = faiss.read_index(str(INDEX_PATH))
        else:
            _index = faiss.IndexFlatL2(VECTOR_DIM)
    return _index


def _load_documents():
    global _documents
    if not _documents and META_PATH.exists():
        with open(str(META_PATH), encoding="utf-8") as f:
            _documents = json.load(f)
    return _documents


def _save_state():
    import faiss
    faiss.write_index(_index, str(INDEX_PATH))
    with open(str(META_PATH), "w", encoding="utf-8") as f:
        json.dump(_documents, f, ensure_ascii=False, indent=2)


def _embed_sync(text: str) -> np.ndarray:
    model = _get_model()
    return model.encode(text, normalize_embeddings=True)


def _add_sync(filename: str, content: str):
    global _documents, _index
    _load_documents()
    _get_index()

    existing = [d for d in _documents if d["filename"] == filename]
    vec = _embed_sync(content).reshape(1, -1).astype(np.float32)

    if existing:
        _documents[_documents.index(existing[0])] = {
            "filename": filename,
            "content": content[:500],
            "updated": datetime.now().isoformat(),
        }
    else:
        _documents.append({
            "filename": filename,
            "content": content[:500],
            "updated": datetime.now().isoformat(),
        })
        _index.add(vec)

    _save_state()


def _remove_sync(filename: str):
    global _documents, _index
    _load_documents()
    _get_index()
    _documents = [d for d in _documents if d["filename"] != filename]
    import faiss
    _index = faiss.IndexFlatL2(VECTOR_DIM)
    _save_state()


def _search_sync(query: str, k: int = 5) -> List[dict]:
    _load_documents()
    _get_index()

    if _index.ntotal == 0 or not _documents:
        return []

    vec = _embed_sync(query).reshape(1, -1).astype(np.float32)
    distances, indices = _index.search(vec, min(k, _index.ntotal))

    results = []
    for i, idx in enumerate(indices[0]):
        if idx < len(_documents) and idx >= 0:
            doc = _documents[idx]
            results.append({
                "filename": doc["filename"],
                "snippet": doc["content"][:300],
                "score": float(1.0 / (1.0 + distances[0][i])),
            })
    return results


async def embed_text(text: str) -> np.ndarray:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _embed_sync, text)


async def add_document(filename: str, content: str):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(_executor, _add_sync, filename, content)


async def remove_document(filename: str):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(_executor, _remove_sync, filename)


async def search(query: str, k: int = 5) -> List[dict]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _search_sync, query, k)


async def rebuild_index():
    global _documents, _index
    import faiss
    from backend.brain_manager import get_all_note_texts

    _documents = []
    _index = faiss.IndexFlatL2(VECTOR_DIM)

    try:
        notes = await get_all_note_texts()
        for note in notes:
            loop = asyncio.get_event_loop()
            vec = (await loop.run_in_executor(_executor, _embed_sync, note["content"])).reshape(1, -1).astype(np.float32)
            _documents.append({
                "filename": note["filename"],
                "content": note["content"][:500],
                "updated": datetime.now().isoformat(),
            })
            _index.add(vec)
        _save_state()
        return len(_documents)
    except Exception as e:
        return 0


def get_stats() -> dict:
    _load_documents()
    _get_index()
    return {
        "documents": len(_documents),
        "vectors": _index.ntotal if _index else 0,
    }
