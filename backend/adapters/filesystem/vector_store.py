"""FileSystemVectorStore — FAISS-based vector search with thread safety."""
import json
import re
import pickle
from pathlib import Path
from typing import Optional

import numpy as np

from backend.ports.search import SearchResult, VectorSearchPort
from backend.infrastructure.logger import get_logger

logger = get_logger("adapters.fs.vectors")

VECTOR_DIM = 384  # all-MiniLM-L6-v2


class FileSystemVectorStore(VectorSearchPort):
    """FAISS-based vector index stored on disk with asyncio.Lock protection."""

    def __init__(self, meta_dir: Path, notes_dir: Path):
        self._meta_dir = meta_dir
        self._notes_dir = notes_dir
        self._lock = None
        self._index = None
        self._documents: list[dict] = []
        self._model = None  # lazy-loaded sentence transformer

    async def _get_lock(self):
        if self._lock is None:
            import asyncio
            self._lock = asyncio.Lock()
        return self._lock

    async def _load_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer("all-MiniLM-L6-v2")
            except ImportError:
                logger.warning("sentence-transformers not available, using fallback")
                return None
        return self._model

    async def _ensure_index(self):
        """Lazy-load index from disk or create new."""
        if self._index is not None:
            return
        index_path = self._meta_dir / "vectors.index"
        docs_path = self._meta_dir / "documents.json"

        if index_path.exists() and docs_path.exists():
            try:
                import faiss
                self._index = faiss.read_index(str(index_path))
                self._documents = json.loads(docs_path.read_text(encoding="utf-8"))
                logger.info("Loaded vector index with %d documents", len(self._documents))
                return
            except Exception as e:
                logger.warning("Failed to load vector index, rebuilding: %s", e)

        # Rebuild from scratch
        await self.rebuild()

    async def search(self, query: str, k: int = 5) -> list[SearchResult]:
        async with await self._get_lock():
            await self._ensure_index()
            if not self._index or not self._documents:
                return []

            model = await self._load_model()
            if not model:
                return []

            try:
                vec = model.encode([query], normalize_embeddings=True).astype(np.float32)
                k = min(k, len(self._documents))
                distances, indices = self._index.search(vec, k)
                results = []
                for i, idx in enumerate(indices[0]):
                    if idx < 0 or idx >= len(self._documents):
                        continue
                    doc = self._documents[idx]
                    score = float(1.0 / (1.0 + distances[0][i]))
                    results.append(SearchResult(
                        filename=doc["filename"],
                        score=score,
                        snippet=doc.get("snippet", ""),
                    ))
                return results
            except Exception as e:
                logger.error("Vector search failed: %s", e)
                return []

    async def add_document(self, filename: str, content: str) -> None:
        async with await self._get_lock():
            await self._ensure_index()
            model = await self._load_model()
            if not model or self._index is None:
                return
            try:
                vec = model.encode([content[:500]], normalize_embeddings=True).astype(np.float32)
                self._index.add(vec)
                self._documents.append({
                    "filename": filename,
                    "content": content[:500],
                    "snippet": content[:200].replace("\n", " ").strip(),
                })
                await self._save_state()
            except Exception as e:
                logger.error("Failed to add document '%s': %s", filename, e)

    async def remove_document(self, filename: str) -> None:
        async with await self._get_lock():
            await self._ensure_index()
            # FAISS doesn't support removal — rebuild from scratch
            idx_to_remove = None
            for i, doc in enumerate(self._documents):
                if doc["filename"] == filename:
                    idx_to_remove = i
                    break
            if idx_to_remove is None:
                return
            self._documents.pop(idx_to_remove)
            await self._rebuild_from_documents()

    async def rebuild(self) -> None:
        async with await self._get_lock():
            try:
                import faiss
                self._index = faiss.IndexFlatL2(VECTOR_DIM)
                self._documents = []

                # Scan all note files
                if not self._notes_dir.exists():
                    await self._save_state()
                    return

                model = await self._load_model()
                if not model:
                    return

                embeddings = []
                for f in sorted(self._notes_dir.rglob("*.md")):
                    if f.name.startswith("_"):
                        continue
                    content = f.read_text(encoding="utf-8", errors="replace")
                    vec = model.encode([content[:500]], normalize_embeddings=True).astype(np.float32)
                    embeddings.append(vec[0])
                    rel = str(f.relative_to(self._notes_dir)).replace("\\", "/")
                    self._documents.append({
                        "filename": rel,
                        "content": content[:500],
                        "snippet": content[:200].replace("\n", " ").strip(),
                    })

                if embeddings:
                    self._index.add(np.array(embeddings, dtype=np.float32))

                await self._save_state()
                logger.info("Vector index rebuilt: %d documents", len(self._documents))
            except Exception as e:
                logger.error("Vector index rebuild failed: %s", e)

    async def _save_state(self) -> None:
        try:
            import faiss
            self._meta_dir.mkdir(parents=True, exist_ok=True)
            faiss.write_index(self._index, str(self._meta_dir / "vectors.index"))
            (self._meta_dir / "documents.json").write_text(
                json.dumps(self._documents, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as e:
            logger.error("Failed to save vector state: %s", e)

    async def _rebuild_from_documents(self) -> None:
        """Rebuild FAISS index from current documents list."""
        try:
            import faiss
            import numpy as np
            self._index = faiss.IndexFlatL2(VECTOR_DIM)
            model = await self._load_model()
            if not model or not self._documents:
                await self._save_state()
                return
            texts = [d["content"] for d in self._documents]
            vecs = model.encode(texts, normalize_embeddings=True).astype(np.float32)
            self._index.add(vecs)
            await self._save_state()
        except Exception as e:
            logger.error("Failed to rebuild from documents: %s", e)
