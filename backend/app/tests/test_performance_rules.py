"""Performance engine tests: known patterns, safe patterns, false positives."""

from app.services.performance_engine import scan_file_performance

JS_SYMBOLS = [(1, 5, "processData()")]
PY_SYMBOLS = [(1, 5, "process_data()")]


def _run(lang, content, symbols=None):
    return scan_file_performance("test." + ("py" if lang == "Python" else "ts"),
                                 lang, content, symbols or [])


class TestNestedLoopDetection:
    def test_for_in_for_flagged(self):
        code = "for a in x:\n    for b in y:\n        print(a, b)"
        findings = _run("Python", code, PY_SYMBOLS)
        assert any("PERF-NESTED-LOOPS" in f["rule_id"] for f in findings)

    def test_for_in_while_flagged(self):
        code = "while items:\n    for x in items:\n        pass"
        findings = _run("Python", code, PY_SYMBOLS)
        assert any("PERF-NESTED-LOOPS" in f["rule_id"] for f in findings)

    def test_single_loop_no_flag(self):
        code = "for x in items:\n    process(x)\n"
        findings = _run("Python", code, PY_SYMBOLS)
        assert not any("PERF-NESTED-LOOPS" in f["rule_id"] for f in findings)


class TestAwaitInLoop:
    def test_await_inside_loop(self):
        code = "for url in urls:\n    resp = await fetch(url)\n"
        findings = _run("JavaScript", code, JS_SYMBOLS)
        assert any("PERF-AWAIT-IN-LOOP" in f["rule_id"] for f in findings)

    def test_no_await_outside_loop(self):
        code = "for url in urls:\n    print(url)\n"
        findings = _run("JavaScript", code, JS_SYMBOLS)
        assert not any("PERF-AWAIT-IN-LOOP" in f["rule_id"] for f in findings)


class TestLinearSearchInLoop:
    def test_indexof_inside_loop(self):
        code = "for x in xs:\n    if arr.indexOf(x) >= 0:\n        hits.push(x)"
        findings = _run("JavaScript", code, JS_SYMBOLS)
        assert any("PERF-LINEAR-SEARCH" in f["rule_id"] for f in findings)


class TestBlockingIO:
    def test_sync_fs_blocked(self):
        code = "const data = fs.readFileSync('big.json')"
        findings = _run("JavaScript", code, JS_SYMBOLS)
        assert any("PERF-SYNC-IO" in f["rule_id"] for f in findings)

    def test_blocking_http_blocked(self):
        code = "r = requests.get('https://api.example.com/data')"
        findings = _run("Python", code, PY_SYMBOLS)
        assert any("PERF-BLOCKING-HTTP" in f["rule_id"] for f in findings)

    def test_async_http_not_flagged(self):
        code = "r = await httpx.AsyncClient().get('https://example.com')"
        findings = _run("JavaScript", code, JS_SYMBOLS)
        assert not any("PERF-BLOCKING-HTTP" in f["rule_id"] for f in findings)


class TestDeepClone:
    def test_json_parse_stringify(self):
        code = "const clone = JSON.parse(JSON.stringify(obj))"
        findings = _run("JavaScript", code, JS_SYMBOLS)
        assert any("PERF-JSON-CLONE" in f["rule_id"] for f in findings)

    def test_structuredClone_safe(self):
        code = "const clone = structuredClone(obj)"
        findings = _run("JavaScript", code, JS_SYMBOLS)
        assert not any("PERF-JSON-CLONE" in f["rule_id"] for f in findings)


class TestLabeling:
    def test_all_findings_are_static(self):
        for lang in ("Python", "JavaScript", "TypeScript"):
            for code in ("for x in a:\n    for y in b:\n        pass",
                         "time.sleep(1)", "import requests; requests.get(u)"):
                for f in _run(lang, code):
                    assert f["measured"] is False
                    assert f["category_label"] == "performance"
                    assert "static analysis" in f["title"].lower() or "Potential Performance Issue" in f["title"]

    def test_large_function_detected(self):
        body = "\n".join(["    x = 1"] * 160)
        code = f"def big(x):\n{body}\n"
        findings = _run("Python", code, [(1, 162, "big()")])
        assert any("PERF-LARGE-FUNCTION" in f["rule_id"] for f in findings)

    def test_all_fields_present(self):
        findings = _run("Python", "time.sleep(1)", PY_SYMBOLS)
        for f in findings:
            for key in ("rule_id", "title", "severity", "confidence", "file",
                        "line", "evidence", "why", "recommendation",
                        "fingerprint", "measured", "note"):
                assert key in f, f"Missing {key}"
