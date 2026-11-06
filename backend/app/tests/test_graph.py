from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

from app.services.graph import (
    _make_imports_rel,
    _make_node_id,
    _merge_rel,
    build_graph_from_parsed,
    delete_graph,
    get_all_nodes,
    get_all_relationships,
    get_graph_summary,
    get_node_detail,
)


# ── Node ID generation ─────────────────────────────────────────────


class TestNodeId:
    def test_make_node_id_basic(self):
        nid = _make_node_id("repo1", "File", "src/index.ts")
        assert nid == "repo1:File::src/index.ts"

    def test_make_node_id_with_name(self):
        nid = _make_node_id("repo1", "Function", "foo", "src/index.ts")
        assert nid == "repo1:Function:src/index.ts:foo"

    def test_make_node_id_unique_per_repo(self):
        a = _make_node_id("repo1", "File", "src/index.ts")
        b = _make_node_id("repo2", "File", "src/index.ts")
        assert a != b

    def test_repo_id_deterministic(self):
        raw = "owner/repo"
        rid = hashlib.sha256(raw.encode()).hexdigest()[:16]
        rid2 = hashlib.sha256(raw.encode()).hexdigest()[:16]
        assert rid == rid2


# ── Mock Neo4j session ────────────────────────────────────────────


class FakeRecord:
    def __init__(self, data: Dict[str, Any]) -> None:
        self._data = data

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def items(self):
        return self._data.items()


class FakeResult:
    def __init__(self, records: List[Dict[str, Any]]) -> None:
        self._records = [FakeRecord(r) for r in records]

    def __iter__(self):
        return iter(self._records)


class FakeSession:
    def __init__(self) -> None:
        self.queries: List[tuple] = []

    def run(self, query: str, **params: Any) -> FakeResult:
        self.queries.append((query, params))
        return FakeResult([])

    def close(self):
        pass


@pytest.fixture
def fake_session():
    return FakeSession()


# ── Merge rel ──────────────────────────────────────────────────────


class TestMergeRel:
    def test_creates_cypher_query(self, fake_session):
        _merge_rel(fake_session, "a1", "b1", "CALLS")
        assert len(fake_session.queries) == 1
        q, p = fake_session.queries[0]
        assert "MERGE" in q
        assert "CALLS" in q
        assert p["from_id"] == "a1"
        assert p["to_id"] == "b1"

    def test_with_properties(self, fake_session):
        _merge_rel(fake_session, "a1", "b1", "IMPORTS", {"source": "./foo"})
        q, p = fake_session.queries[0]
        assert "source" in q
        assert p["source"] == "./foo"


# ── Build graph from parsed (mocked session) ──────────────────────


SAMPLE_PARSED = [
    {
        "file_path": "src/index.ts",
        "language": "typescript",
        "functions": [
            {"name": "main", "start_line": 1, "end_line": 10, "is_async": False, "is_exported": True},
        ],
        "classes": [
            {"name": "App", "start_line": 15, "end_line": 50, "extends": "Component", "is_exported": True},
        ],
        "methods": [
            {"name": "render", "class_name": "App", "start_line": 20, "end_line": 30, "is_async": False},
        ],
        "imports": [
            {"source": "react", "names": ["React"], "import_kind": "default"},
        ],
        "exports": [],
        "calls": [
            {"name": "main"},
        ],
    },
    {
        "file_path": "src/utils.ts",
        "language": "typescript",
        "functions": [
            {"name": "helper", "start_line": 1, "end_line": 5, "is_async": False, "is_exported": False},
        ],
        "classes": [],
        "methods": [],
        "imports": [],
        "exports": [],
        "calls": [],
    },
]


class TestBuildGraph:
    @patch("app.services.graph.get_session")
    def test_build_creates_nodes_and_rels(self, mock_get_session):
        session = FakeSession()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        result = build_graph_from_parsed("repo1", "testowner", "testrepo", SAMPLE_PARSED)

        assert result["status"] == "ok"
        assert result["repo_id"] == "repo1"
        assert result["stats"]["files"] == 2
        assert result["stats"]["functions"] == 2
        assert result["stats"]["classes"] == 1
        assert result["stats"]["methods"] == 1

    @patch("app.services.graph.get_session")
    def test_build_no_neo4j(self, mock_get_session):
        mock_get_session.return_value.__enter__ = MagicMock(return_value=None)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        result = build_graph_from_parsed("repo1", "o", "r", [])
        assert result["status"] == "error"
        assert "Neo4j" in result["message"]

    @patch("app.services.graph.get_session")
    def test_build_empty_parsed(self, mock_get_session):
        session = FakeSession()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        result = build_graph_from_parsed("repo1", "o", "r", [])
        assert result["status"] == "ok"
        assert result["stats"]["files"] == 0


# ── Graph queries (mocked session) ────────────────────────────────


class TestGraphQueries:
    @patch("app.services.graph.get_session")
    def test_get_summary_returns_none(self, mock_get_session):
        mock_get_session.return_value.__enter__ = MagicMock(return_value=None)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)
        assert get_graph_summary("repo1") is None

    @patch("app.services.graph.get_session")
    def test_get_node_detail_returns_none(self, mock_get_session):
        mock_get_session.return_value.__enter__ = MagicMock(return_value=None)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)
        assert get_node_detail("repo1", "node1") is None

    @patch("app.services.graph.get_session")
    def test_get_all_nodes_returns_empty(self, mock_get_session):
        mock_get_session.return_value.__enter__ = MagicMock(return_value=None)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)
        assert get_all_nodes("repo1") == []

    @patch("app.services.graph.get_session")
    def test_get_all_relationships_returns_empty(self, mock_get_session):
        mock_get_session.return_value.__enter__ = MagicMock(return_value=None)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)
        assert get_all_relationships("repo1") == []

    @patch("app.services.graph.get_session")
    def test_delete_graph_returns_false(self, mock_get_session):
        mock_get_session.return_value.__enter__ = MagicMock(return_value=None)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)
        assert delete_graph("repo1") is False


# ── Graph build with cross-file imports ────────────────────────────


CROSS_FILE_PARSED = [
    {
        "file_path": "src/app.ts",
        "language": "typescript",
        "functions": [
            {"name": "bootstrap", "start_line": 1, "end_line": 5, "is_async": False, "is_exported": False},
        ],
        "classes": [],
        "methods": [],
        "imports": [
            {"source": "src/utils.ts", "names": ["helper"], "import_kind": "named"},
        ],
        "exports": [],
        "calls": [
            {"name": "helper"},
        ],
    },
    {
        "file_path": "src/utils.ts",
        "language": "typescript",
        "functions": [
            {"name": "helper", "start_line": 1, "end_line": 3, "is_async": True, "is_exported": True},
        ],
        "classes": [],
        "methods": [],
        "imports": [],
        "exports": [],
        "calls": [],
    },
]


class TestCrossFileGraph:
    @patch("app.services.graph.get_session")
    def test_cross_file_imports(self, mock_get_session):
        session = FakeSession()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        result = build_graph_from_parsed("repo2", "o", "r", CROSS_FILE_PARSED)
        assert result["stats"]["imports"] == 1
        assert result["stats"]["functions"] == 2


# ── Class extends graph ────────────────────────────────────────────


CLASS_HIERARCHY_PARSED = [
    {
        "file_path": "src/base.ts",
        "language": "typescript",
        "functions": [],
        "classes": [
            {"name": "BaseService", "start_line": 1, "end_line": 20, "extends": None, "is_exported": True},
        ],
        "methods": [
            {"name": "init", "class_name": "BaseService", "start_line": 5, "end_line": 10, "is_async": False},
        ],
        "imports": [],
        "exports": [],
        "calls": [],
    },
    {
        "file_path": "src/user.ts",
        "language": "typescript",
        "functions": [],
        "classes": [
            {"name": "UserService", "start_line": 1, "end_line": 30, "extends": "BaseService", "is_exported": True},
        ],
        "methods": [
            {"name": "create", "class_name": "UserService", "start_line": 10, "end_line": 20, "is_async": True},
        ],
        "imports": [
            {"source": "src/base.ts", "names": ["BaseService"], "import_kind": "named"},
        ],
        "exports": [],
        "calls": [],
    },
]


class TestClassHierarchyGraph:
    @patch("app.services.graph.get_session")
    def test_extends_relationship(self, mock_get_session):
        session = FakeSession()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        result = build_graph_from_parsed("repo3", "o", "r", CLASS_HIERARCHY_PARSED)
        assert result["stats"]["classes"] == 2
        assert result["stats"]["extends"] == 1
        assert result["stats"]["methods"] == 2


# ── API endpoint tests ─────────────────────────────────────────────


class TestGraphAPI:
    def test_repo_id_matches(self):
        from app.api.graph import _repo_id
        rid = _repo_id("myuser", "myrepo")
        assert len(rid) == 16
        assert _repo_id("myuser", "myrepo") == rid
        assert _repo_id("myuser", "other") != rid
