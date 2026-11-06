from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.services.ai import (
    _extract_sources,
    _search_nodes_by_keywords,
    _search_rels_for_nodes,
    answer_question,
    append_history,
    build_context,
    clear_history,
    get_history,
)


# ── Fixtures ──────────────────────────────────────────────────────

def _node(name: str, label: str = "Function", file_path: str = "src/app.ts", **extra):
    n = {"node_id": f"r:{label}:{file_path}:{name}", "name": name, "label": label, "file_path": file_path}
    n.update(extra)
    return n


def _rel(from_name: str, rel_type: str, to_name: str, from_fp: str = "src/app.ts", to_fp: str = "src/app.ts"):
    return {
        "type": rel_type,
        "from_id": f"r:Function:{from_fp}:{from_name}",
        "from_name": from_name,
        "to_id": f"r:Function:{to_fp}:{to_name}",
        "to_name": to_name,
    }


# ── Context retrieval tests ───────────────────────────────────────

class TestSearchNodes:
    def test_exact_name_match(self):
        nodes = [_node("validateToken"), _node("getUser"), _node("formatDate")]
        result = _search_nodes_by_keywords(nodes, ["validatetoken"])
        assert len(result) >= 1
        assert result[0]["name"] == "validateToken"

    def test_partial_keyword_match(self):
        nodes = [_node("UserService"), _node("AuthMiddleware"), _node("TokenRepo")]
        result = _search_nodes_by_keywords(nodes, ["user"])
        names = [n["name"] for n in result]
        assert "UserService" in names

    def test_no_matches_returns_empty(self):
        nodes = [_node("foo"), _node("bar")]
        result = _search_nodes_by_keywords(nodes, ["zzzznotfound"])
        assert result == []

    def test_file_path_search(self):
        nodes = [_node("helper", file_path="src/utils/auth.ts")]
        result = _search_nodes_by_keywords(nodes, ["auth"])
        assert len(result) == 1

    def test_limits_to_30(self):
        nodes = [_node(f"fn_{i}") for i in range(50)]
        result = _search_nodes_by_keywords(nodes, ["fn"])
        assert len(result) == 30

    def test_ranks_by_relevance(self):
        nodes = [
            _node("auth_validate", file_path="src/auth.ts"),
            _node("auth_helper", file_path="src/auth.ts"),
            _node("unrelated", file_path="src/other.ts"),
        ]
        result = _search_nodes_by_keywords(nodes, ["auth"])
        assert result[0]["name"] in ("auth_validate", "auth_helper")


class TestSearchRels:
    def test_finds_outgoing(self):
        rels = [_rel("a", "CALLS", "b"), _rel("c", "IMPORTS", "d")]
        result = _search_rels_for_nodes(rels, {"r:Function:src/app.ts:a"})
        assert len(result) == 1
        assert result[0]["from_name"] == "a"

    def test_finds_incoming(self):
        rels = [_rel("a", "CALLS", "b")]
        result = _search_rels_for_nodes(rels, {"r:Function:src/app.ts:b"})
        assert len(result) == 1

    def test_no_matches(self):
        rels = [_rel("a", "CALLS", "b")]
        result = _search_rels_for_nodes(rels, {"r:Function:src/app.ts:z"})
        assert result == []


# ── Context building tests ────────────────────────────────────────

class TestBuildContext:
    def test_includes_repo_info(self):
        ctx = build_context("how does auth work?", [], [], "acme", "repo")
        assert "acme/repo" in ctx

    def test_includes_nodes(self):
        nodes = [_node("validateToken")]
        ctx = build_context("validate token", nodes, [])
        assert "validateToken" in ctx

    def test_includes_relationships(self):
        rels = [_rel("caller", "CALLS", "callee")]
        nodes = [_node("caller"), _node("callee")]
        ctx = build_context("who calls callee", nodes, rels)
        assert "CALLS" in ctx

    def test_truncates_long_context(self):
        nodes = [_node(f"very_long_function_name_{i}", file_path=f"src/file_{i}.ts") for i in range(200)]
        ctx = build_context("find functions", nodes, [])
        assert len(ctx) <= 42_000

    def test_empty_nodes_falls_back(self):
        nodes = [_node("a"), _node("b")]
        ctx = build_context("zzzznothing", nodes, [])
        assert "a" in ctx
        assert "b" in ctx


# ── Conversation history tests ────────────────────────────────────

class TestConversationHistory:
    def test_empty_initially(self):
        clear_history("o", "r", "tok")
        h = get_history("o", "r", "tok")
        assert h == []

    def test_append_and_get(self):
        clear_history("o", "r", "tok")
        append_history("o", "r", "tok", "user", "hello")
        append_history("o", "r", "tok", "assistant", "hi there")
        h = get_history("o", "r", "tok")
        assert len(h) == 2
        assert h[0]["role"] == "user"
        assert h[1]["role"] == "assistant"

    def test_clear(self):
        append_history("o", "r", "tok", "user", "hello")
        clear_history("o", "r", "tok")
        assert get_history("o", "r", "tok") == []

    def test_different_tokens_separate(self):
        clear_history("o", "r", "tok1")
        clear_history("o", "r", "tok2")
        append_history("o", "r", "tok1", "user", "q1")
        append_history("o", "r", "tok2", "user", "q2")
        assert len(get_history("o", "r", "tok1")) == 1
        assert len(get_history("o", "r", "tok2")) == 1
        clear_history("o", "r", "tok1")
        clear_history("o", "r", "tok2")

    def test_limits_history(self):
        clear_history("o", "r", "tok")
        for i in range(25):
            append_history("o", "r", "tok", "user", f"q{i}")
        h = get_history("o", "r", "tok")
        assert len(h) <= 20
        clear_history("o", "r", "tok")


# ── Source extraction tests ───────────────────────────────────────

class TestExtractSources:
    def test_extracts_backtick_files(self):
        answer = "See `src/auth.ts:42` for details."
        sources = _extract_sources(answer, [])
        assert any(s["file"] == "src/auth.ts" for s in sources)

    def test_extracts_plain_files(self):
        answer = "The function in src/utils/helpers.ts is used."
        sources = _extract_sources(answer, [])
        assert any("src/utils/helpers.ts" in s["file"] for s in sources)

    def test_no_sources(self):
        answer = "I don't know."
        sources = _extract_sources(answer, [])
        assert sources == []

    def test_deduplicates(self):
        answer = "See `src/auth.ts:10` and also `src/auth.ts:10` again."
        sources = _extract_sources(answer, [])
        file_lines = [(s["file"], s["line"]) for s in sources]
        assert len(file_lines) == len(set(file_lines))

    def test_from_node_context(self):
        nodes = [_node("getUser", file_path="src/api/user.ts", start_line=10)]
        answer = "The getUser function in src/api/user.ts handles requests."
        sources = _extract_sources(answer, nodes)
        assert any("src/api/user.ts" in s["file"] for s in sources)


# ── Answer generation tests ───────────────────────────────────────

@pytest.mark.asyncio
async def test_answer_without_llm():
    clear_history("o", "r", "tok")
    with patch("app.services.ai._get_api_config", return_value=None):
        result = await answer_question(
            question="how does auth work?",
            nodes=[_node("validateToken")],
            rels=[],
            owner="acme",
            repo="repo",
            user_token="tok",
        )
    assert result["error"] == "LLM not configured"
    assert "not configured" in result["answer"]
    clear_history("o", "r", "tok")


@pytest.mark.asyncio
async def test_answer_with_mock_llm():
    clear_history("o", "r", "tok")
    mock_response = "Authentication works via `src/auth.ts:12`. The `validateToken` function verifies JWT tokens."
    with (
        patch("app.services.ai._get_api_config", return_value={"api_key": "test", "base_url": "http://x", "model": "m"}),
        patch("app.services.ai._call_llm", new_callable=AsyncMock, return_value=mock_response),
    ):
        result = await answer_question(
            question="how does auth work?",
            nodes=[_node("validateToken", file_path="src/auth.ts", start_line=12)],
            rels=[],
            owner="acme",
            repo="repo",
            user_token="tok",
        )
    assert result["error"] is None
    assert "validateToken" in result["answer"]
    assert len(result["sources"]) > 0
    clear_history("o", "r", "tok")
