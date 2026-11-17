import json
from pathlib import Path
from typing import Protocol

import faiss
import numpy as np
from pydantic import BaseModel

from regulaai.rag.chunking import PolicyChunk


class Embedder(Protocol):
    def embed_documents(self, texts: list[str]) -> np.ndarray: ...
    def embed_query(self, text: str) -> np.ndarray: ...


class SearchHit(BaseModel):
    chunk: PolicyChunk
    score: float  # cosine similarity: closer to 1.0 means more similar


def _prepare(vectors) -> np.ndarray:
    arr = np.ascontiguousarray(vectors, dtype="float32")
    faiss.normalize_L2(arr)  # after this, inner product == cosine similarity
    return arr


class PolicyIndex:
    def __init__(self, embedder: Embedder) -> None:
        self._embedder = embedder
        self._index: faiss.Index | None = None
        self._chunks: list[PolicyChunk] = []

    def build(self, chunks: list[PolicyChunk]) -> None:
        texts = [f"{c.source} - {c.section}\n{c.text}" for c in chunks]
        vectors = _prepare(self._embedder.embed_documents(texts))
        self._index = faiss.IndexFlatIP(vectors.shape[1])
        self._index.add(vectors)
        self._chunks = list(chunks)

    def search(self, query: str, k: int = 3) -> list[SearchHit]:
        if self._index is None:
            raise RuntimeError("Index is empty. Call build() or load() first.")
        q = _prepare(np.asarray(self._embedder.embed_query(query)).reshape(1, -1))
        scores, ids = self._index.search(q, min(k, len(self._chunks)))
        return [
            SearchHit(chunk=self._chunks[i], score=float(s))
            for s, i in zip(scores[0], ids[0])
            if i != -1
        ]

    def save(self, directory: str | Path) -> None:
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self._index, str(directory / "policies.faiss"))
        data = [c.model_dump() for c in self._chunks]
        (directory / "chunks.json").write_text(json.dumps(data), encoding="utf-8")

    @classmethod
    def load(cls, directory: str | Path, embedder: Embedder) -> "PolicyIndex":
        directory = Path(directory)
        obj = cls(embedder)
        obj._index = faiss.read_index(str(directory / "policies.faiss"))
        raw = json.loads((directory / "chunks.json").read_text(encoding="utf-8"))
        obj._chunks = [PolicyChunk(**c) for c in raw]
        return obj