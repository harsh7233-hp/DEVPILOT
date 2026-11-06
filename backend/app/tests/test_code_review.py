from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.services.code_review import (
    ReviewIssue,
    ReviewResult,
    run_static_checks,
    _parse_ai_response,
    _build_repo_context,
    review_code,
)


# ── Static checks tests ───────────────────────────────────────────

class TestStaticChecksJS:
    def test_console_log(self):
        issues = run_static_checks("console.log('hello');", "TypeScript", "test.ts")
        assert len(issues) == 1
        assert issues[0].severity == "LOW"
        assert issues[0].title == "Console statement found"
        assert issues[0].line == 1
        assert issues[0].source == "static"

    def test_console_error(self):
        issues = run_static_checks("console.error('fail');", "JavaScript", "test.js")
        assert len(issues) == 1

    def test_eval(self):
        code = "eval(userInput);"
        issues = run_static_checks(code, "TypeScript", "test.ts")
        assert any(i.severity == "CRITICAL" for i in issues)

    def test_var_declaration(self):
        code = "var x = 1;"
        issues = run_static_checks(code, "TypeScript", "test.ts")
        assert any(i.title == "var declaration used" for i in issues)

    def test_empty_catch(self):
        code = "try { foo(); } catch (e) {}"
        issues = run_static_checks(code, "TypeScript", "test.ts")
        assert any(i.title == "Empty catch block" for i in issues)

    def test_loose_equality(self):
        code = "if (x == 1) {}"
        issues = run_static_checks(code, "TypeScript", "test.ts")
        assert any("Loose equality" in i.title for i in issues)

    def test_loose_inequality(self):
        code = "if (x != 1) {}"
        issues = run_static_checks(code, "TypeScript", "test.ts")
        assert any("Loose inequality" in i.title for i in issues)

    def test_todo_comment(self):
        code = "// TODO: fix this"
        issues = run_static_checks(code, "TypeScript", "test.ts")
        assert any("TODO" in i.title for i in issues)

    def test_hardcoded_secret(self):
        code = 'const apiKey = "sk-1234567890abcdef";'
        issues = run_static_checks(code, "TypeScript", "test.ts")
        assert any(i.severity == "CRITICAL" for i in issues)

    def test_new_function(self):
        code = "const fn = new Function('return 1');"
        issues = run_static_checks(code, "TypeScript", "test.ts")
        assert any(i.title == "Dynamic function constructor detected" for i in issues)

    def test_multiple_issues(self):
        code = """
console.log('debug');
var x = 1;
eval(code);
"""
        issues = run_static_checks(code, "TypeScript", "test.ts")
        assert len(issues) >= 3

    def test_clean_code(self):
        code = "const x: number = 1;\nconst y: number = 2;"
        issues = run_static_checks(code, "TypeScript", "test.ts")
        assert len(issues) == 0


class TestStaticChecksPython:
    def test_bare_except(self):
        code = "try:\n    foo()\nexcept:\n    pass"
        issues = run_static_checks(code, "Python", "test.py")
        assert any(i.title == "Bare except clause" for i in issues)

    def test_eval_python(self):
        code = "result = eval(user_input)"
        issues = run_static_checks(code, "Python", "test.py")
        assert any(i.severity == "CRITICAL" for i in issues)

    def test_exec(self):
        code = "exec(code_string)"
        issues = run_static_checks(code, "Python", "test.py")
        assert any(i.severity == "CRITICAL" for i in issues)

    def test_wildcard_import(self):
        code = "from os import *"
        issues = run_static_checks(code, "Python", "test.py")
        assert any("Wildcard import" in i.title for i in issues)

    def test_todo_python(self):
        code = "# FIXME: broken"
        issues = run_static_checks(code, "Python", "test.py")
        assert any("TODO" in i.title or "FIXME" in i.title for i in issues)


# ── AI response parsing tests ─────────────────────────────────────

class TestParseAIResponse:
    def test_valid_json(self):
        response = json.dumps([
            {"severity": "HIGH", "title": "Bug", "explanation": "This is wrong", "file": "x.ts", "line": 10, "suggestion": "Fix it", "source": "ai"}
        ])
        issues = _parse_ai_response(response, "x.ts")
        assert len(issues) == 1
        assert issues[0].severity == "HIGH"
        assert issues[0].source == "ai"

    def test_json_in_code_block(self):
        response = '```json\n[{"severity": "LOW", "title": "Style", "explanation": "Minor", "suggestion": "Improve"}]\n```'
        issues = _parse_ai_response(response, "x.ts")
        assert len(issues) == 1

    def test_json_with_surrounding_text(self):
        response = 'Here are the issues:\n[{"severity": "MEDIUM", "title": "Issue", "explanation": "Bad", "suggestion": "Fix"}]\nDone.'
        issues = _parse_ai_response(response, "x.ts")
        assert len(issues) == 1

    def test_invalid_json(self):
        issues = _parse_ai_response("This is not JSON at all", "x.ts")
        assert issues == []

    def test_empty_array(self):
        issues = _parse_ai_response("[]", "x.ts")
        assert issues == []

    def test_invalid_severity_falls_back(self):
        response = json.dumps([{"severity": "INVALID", "title": "X", "explanation": "Y", "suggestion": "Z"}])
        issues = _parse_ai_response(response, "x.ts")
        assert issues[0].severity == "LOW"

    def test_missing_fields(self):
        response = json.dumps([{"title": "Only title"}])
        issues = _parse_ai_response(response, "x.ts")
        assert len(issues) == 1
        assert issues[0].file == "x.ts"
        assert issues[0].severity == "LOW"


# ── Review issue/result tests ─────────────────────────────────────

class TestReviewIssue:
    def test_to_dict(self):
        issue = ReviewIssue("HIGH", "Bug", "Bad code", "x.ts", 10, "Fix it", "ai")
        d = issue.to_dict()
        assert d["severity"] == "HIGH"
        assert d["title"] == "Bug"
        assert d["file"] == "x.ts"
        assert d["line"] == 10
        assert d["source"] == "ai"

    def test_to_dict_no_line(self):
        issue = ReviewIssue("LOW", "Style", "Minor", "x.ts")
        d = issue.to_dict()
        assert "line" not in d


class TestReviewResult:
    def test_to_dict_sorted(self):
        result = ReviewResult()
        result.issues = [
            ReviewIssue("LOW", "A", "a"),
            ReviewIssue("CRITICAL", "B", "b"),
            ReviewIssue("HIGH", "C", "c"),
        ]
        d = result.to_dict()
        assert d["issues"][0]["severity"] == "CRITICAL"
        assert d["issues"][1]["severity"] == "HIGH"
        assert d["issues"][2]["severity"] == "LOW"
        assert d["counts"]["CRITICAL"] == 1
        assert d["total"] == 3


# ── Repo context tests ────────────────────────────────────────────

class TestBuildRepoContext:
    def test_includes_file_entities(self):
        nodes = [
            {"node_id": "r:File:x.ts", "label": "File", "name": "x.ts", "file_path": "x.ts"},
            {"node_id": "r:Function:x.ts:foo", "label": "Function", "name": "foo", "file_path": "x.ts"},
        ]
        ctx = _build_repo_context(nodes, [], "x.ts")
        assert "foo" in ctx

    def test_includes_incoming_rels(self):
        nodes = [{"node_id": "r:Function:x.ts:foo", "label": "Function", "name": "foo", "file_path": "x.ts"}]
        rels = [{"type": "CALLS", "from_id": "r:Function:y.ts:bar", "from_name": "bar", "to_id": "r:Function:x.ts:foo", "to_name": "foo"}]
        ctx = _build_repo_context(nodes, rels, "x.ts")
        assert "CALLS" in ctx

    def test_empty_context(self):
        ctx = _build_repo_context([], [], "nonexistent.ts")
        assert ctx == ""


# ── Full pipeline tests ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_review_code_without_llm():
    with patch("app.services.ai._get_api_config", return_value=None):
        result = await review_code(
            code="console.log('test');",
            language="TypeScript",
            file_path="test.ts",
        )
    assert result["total"] >= 1
    assert result["static_count"] >= 1
    assert "console" in result["issues"][0]["title"].lower() or any(
        "console" in i["title"].lower() for i in result["issues"]
    )


@pytest.mark.asyncio
async def test_review_code_with_mock_llm():
    mock_response = json.dumps([
        {"severity": "MEDIUM", "title": "AI suggestion", "explanation": "Consider refactoring", "suggestion": "Break into smaller functions", "source": "ai"}
    ])
    with (
        patch("app.services.ai._get_api_config", return_value={"api_key": "test", "base_url": "http://x", "model": "m"}),
        patch("app.services.code_review._call_llm", new_callable=AsyncMock, return_value=mock_response),
    ):
        result = await review_code(
            code="const x = 1;",
            language="TypeScript",
            file_path="test.ts",
        )
    assert result["total"] >= 1
    assert result["ai_count"] >= 1
    assert any(i["source"] == "ai" for i in result["issues"])


@pytest.mark.asyncio
async def test_review_clean_code():
    with patch("app.services.code_review._get_api_config", return_value=None), \
         patch("app.services.ai._get_api_config", return_value=None):
        result = await review_code(
            code="const x: number = 1;\nconst y: number = 2;",
            language="TypeScript",
            file_path="clean.ts",
        )
    assert result["static_count"] == 0
    assert "good" in result["summary"].lower() or result["total"] == 0


@pytest.mark.asyncio
async def test_review_with_diff():
    diff = "+const secret = 'sk-1234';"
    with patch("app.services.ai._get_api_config", return_value=None):
        result = await review_code(
            code="const x = 1;",
            language="TypeScript",
            file_path="test.ts",
            diff=diff,
        )
    assert result["total"] >= 1
