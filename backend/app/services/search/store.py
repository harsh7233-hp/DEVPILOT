from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from app.services.search.embeddings import cosine_similarity


class VectorStore:
    __slots__ = ("_vectors", "_chunks", "_indexed")

    def __init__(self) -> None:
        self._vectors: List[List[float]] = []
        self._chunks: List[Dict[str, Any]] = []
        self._indexed: bool = False

    @property
    def count(self) -> int:
        return len(self._chunks)

    @property
    def is_indexed(self) -> bool:
        return self._indexed

    def add(self, vectors: List[List[float]], chunks: List[Dict[str, Any]]) -> None:
        if len(vectors) != len(chunks):
            raise ValueError("vectors and chunks must have same length")
        self._vectors.extend(vectors)
        self._chunks.extend(chunks)
        self._indexed = len(self._vectors) > 0

    def search(
        self,
        query_vector: List[float],
        top_k: int = 10,
        min_score: float = 0.0,
    ) -> List[Tuple[Dict[str, Any], float]]:
        if not self._vectors:
            return []

        scored: List[Tuple[int, float]] = []
        for i, vec in enumerate(self._vectors):
            score = cosine_similarity(query_vector, vec)
            if score >= min_score:
                scored.append((i, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        results: List[Tuple[Dict[str, Any], float]] = []
        for idx, score in scored[:top_k]:
            results.append((self._chunks[idx], score))
        return results

    def clear(self) -> None:
        self._vectors.clear()
        self._chunks.clear()
        self._indexed = False


_stores: Dict[str, VectorStore] = {}


def get_store(repo_id: str) -> VectorStore:
    if repo_id not in _stores:
        _stores[repo_id] = VectorStore()
    return _stores[repo_id]


def delete_store(repo_id: str) -> bool:
    if repo_id in _stores:
        del _stores[repo_id]
        return True
    return False
