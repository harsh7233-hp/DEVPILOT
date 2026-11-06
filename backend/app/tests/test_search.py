from __future__ import annotations

import math
from unittest.mock import AsyncMock, patch

import pytest

from app.services.search.chunker import CodeChunk, chunk_all_files, chunk_parsed_file
from app.services.search.embeddings import cosine_similarity
from app.services.search.store import VectorStore, get_store, delete_store


# ── Chunker tests ─────────────────────────────────────────────────

SAMPLE_SOURCE = """import { foo } from 'bar';
import { baz } from 'qux';

export function validateToken(token: string): Promise<boolean> {
  const decoded = decode(token);
  if (!decoded) return false;
  return true;
}

export class AuthService {
  async login(user: string, pass: string): Promise<boolean> {
    return true;
  }

  async logout(): Promise<void> {
    // clear session
  }
}
"""


def _parsed():
    return {
        "file_path": "src/auth.ts",
        "language": "TypeScript",
        "functions": [
            {"name": "validateToken", "start_line": 4, "end_line": 8}
        ],
        "classes": [
            {"name": "AuthService", "start_line": 10, "end_line": 22}
        ],
        "methods": [
            {"name": "login", "class_name": "AuthService", "start_line": 12, "end_line": 15},
            {"name": "logout", "class_name": "AuthService", "start_line": 17, "end_line": 20},
        ],
        "imports": [
            {"start_line": 1, "end_line": 1},
            {"start_line": 2, "end_line": 2},
        ],
        "exports": [],
        "calls": [],
    }


class TestChunkParsedFile:
    def test_chunks_function(self):
        chunks = chunk_parsed_file(_parsed(), SAMPLE_SOURCE)
        fn_chunks = [c for c in chunks if c.entity_kind == "function"]
        assert len(fn_chunks) == 1
        assert fn_chunks[0].entity_name == "validateToken"
        assert "decode" in fn_chunks[0].snippet

    def test_chunks_class(self):
        chunks = chunk_parsed_file(_parsed(), SAMPLE_SOURCE)
        cls_chunks = [c for c in chunks if c.entity_kind == "class"]
        assert len(cls_chunks) == 1
        assert cls_chunks[0].entity_name == "AuthService"

    def test_chunks_methods(self):
        chunks = chunk_parsed_file(_parsed(), SAMPLE_SOURCE)
        method_chunks = [c for c in chunks if c.entity_kind == "method"]
        assert len(method_chunks) == 2
        names = {c.entity_name for c in method_chunks}
        assert "AuthService.login" in names
        assert "AuthService.logout" in names

    def test_chunks_imports(self):
        chunks = chunk_parsed_file(_parsed(), SAMPLE_SOURCE)
        imp_chunks = [c for c in chunks if c.entity_kind == "imports"]
        assert len(imp_chunks) == 1
        assert "foo" in imp_chunks[0].snippet

    def test_all_chunks_have_file_path(self):
        chunks = chunk_parsed_file(_parsed(), SAMPLE_SOURCE)
        for c in chunks:
            assert c.file_path == "src/auth.ts"

    def test_to_dict(self):
        chunks = chunk_parsed_file(_parsed(), SAMPLE_SOURCE)
        d = chunks[0].to_dict()
        assert "file_path" in d
        assert "entity_name" in d
        assert "snippet" in d

    def test_empty_parsed(self):
        chunks = chunk_parsed_file({"file_path": "empty.ts"}, "")
        assert chunks == []

    def test_fallback_to_raw_blocks(self):
        parsed = {"file_path": "raw.ts", "functions": [], "classes": [], "methods": [], "imports": []}
        source = "line1\nline2\nline3"
        chunks = chunk_parsed_file(parsed, source)
        assert len(chunks) >= 1
        assert chunks[0].entity_kind == "file"


class TestChunkAllFiles:
    def test_multiple_files(self):
        parsed_files = [_parsed(), _parsed()]
        sources = {"src/auth.ts": SAMPLE_SOURCE}
        chunks = chunk_all_files(parsed_files, sources)
        assert len(chunks) > 0

    def test_missing_source(self):
        parsed_files = [_parsed()]
        chunks = chunk_all_files(parsed_files, {})
        assert chunks == []


# ── Cosine similarity tests ───────────────────────────────────────

class TestCosineSimilarity:
    def test_identical_vectors(self):
        v = [1.0, 2.0, 3.0]
        assert cosine_similarity(v, v) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        assert cosine_similarity([1, 0], [0, 1]) == pytest.approx(0.0)

    def test_opposite_vectors(self):
        assert cosine_similarity([1, 0], [-1, 0]) == pytest.approx(-1.0)

    def test_zero_vector(self):
        assert cosine_similarity([0, 0], [1, 2]) == 0.0

    def test_similar_vectors_high_score(self):
        a = [1.0, 2.0, 3.0]
        b = [1.1, 2.1, 2.9]
        assert cosine_similarity(a, b) > 0.99


# ── Vector store tests ────────────────────────────────────────────

class TestVectorStore:
    def test_empty_store(self):
        store = VectorStore()
        assert store.count == 0
        assert store.is_indexed is False
        results = store.search([1.0, 0.0])
        assert results == []

    def test_add_and_search(self):
        store = VectorStore()
        chunks = [
            {"file_path": "a.ts", "entity_name": "foo", "entity_kind": "function", "snippet": "code a"},
            {"file_path": "b.ts", "entity_name": "bar", "entity_kind": "function", "snippet": "code b"},
        ]
        vectors = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]
        store.add(vectors, chunks)
        assert store.count == 2
        assert store.is_indexed is True

        results = store.search([1.0, 0.0, 0.0], top_k=1)
        assert len(results) == 1
        assert results[0][0]["entity_name"] == "foo"
        assert results[0][1] == pytest.approx(1.0)

    def test_search_top_k(self):
        store = VectorStore()
        chunks = [{"entity_name": f"fn_{i}"} for i in range(20)]
        vectors = [[float(i), 0.0] for i in range(20)]
        store.add(vectors, chunks)
        results = store.search([1.0, 0.0], top_k=5)
        assert len(results) == 5

    def test_search_min_score(self):
        store = VectorStore()
        chunks = [{"entity_name": "a"}, {"entity_name": "b"}]
        vectors = [[1.0, 0.0], [0.0, 1.0]]
        store.add(vectors, chunks)
        results = store.search([1.0, 0.0], min_score=0.9)
        assert len(results) == 1

    def test_clear(self):
        store = VectorStore()
        store.add([[1.0]], [{"name": "x"}])
        store.clear()
        assert store.count == 0
        assert store.is_indexed is False

    def test_length_mismatch_raises(self):
        store = VectorStore()
        with pytest.raises(ValueError):
            store.add([[1.0], [2.0]], [{"name": "x"}])


# ── Store registry tests ──────────────────────────────────────────

class TestStoreRegistry:
    def test_get_store_creates(self):
        delete_store("test_repo")
        store = get_store("test_repo")
        assert store.count == 0
        delete_store("test_repo")

    def test_get_store_returns_same(self):
        delete_store("test_repo")
        s1 = get_store("test_repo")
        s2 = get_store("test_repo")
        assert s1 is s2
        delete_store("test_repo")

    def test_delete_store(self):
        get_store("test_repo")
        assert delete_store("test_repo") is True
        assert delete_store("test_repo") is False
