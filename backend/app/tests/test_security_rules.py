"""Module 2 security engine tests: rules, confidence, evidence, standards."""

from __future__ import annotations

from app.services.security_rules import (
    RULES,
    detect_committed_env_files,
    rule_applicable,
    scan_file_security,
)


def run(path, lang, content, symbols=None):
    findings, executed = scan_file_security(path, lang, content, symbols or [])
    return findings, executed


class TestRuleApplicability:
    def test_python_rule_not_run_for_js(self):
        sql = next(r for r in RULES if r.id == "PY-SQL-FSTRING")
        assert not rule_applicable(sql, "a.ts", "TypeScript")
        assert rule_applicable(sql, "a.py", "Python")

    def test_django_settings_only(self):
        dbg = next(r for r in RULES if r.id == "DJANGO-DEBUG-TRUE")
        assert not rule_applicable(dbg, "app/main.py", "Python")
        assert not rule_applicable(dbg, "app/settings.py", "JavaScript")
        assert rule_applicable(dbg, "myproject/settings.py", "Python")


class TestVulnerableCases:
    def test_sql_injection_fstring_detected(self):
        findings, _ = run("db.py", "Python",
                          'q = f"SELECT * FROM users WHERE id={uid}"')
        f = next(f for f in findings if f["rule_id"] == "PY-SQL-FSTRING")
        assert f["severity"] == "HIGH"
        assert f["confidence"] == "MEDIUM"
        assert "SELECT" in f["evidence"]
        assert any(s["id"] == "A03" for s in f["standards"])

    def test_shell_true_command_injection(self):
        findings, _ = run("x.py", "Python",
                          'subprocess.run("ls " + user_dir, shell=True)')
        f = next(f for f in findings if f["rule_id"] == "PY-CMD-SHELLTRUE")
        assert f["severity"] == "CRITICAL"
        assert f["manual_review_required"] is True

    def test_tls_disabled_high_confidence(self):
        findings, _ = run("c.js", "JavaScript",
                          "https.get(url, { rejectUnauthorized: false }, cb)")
        f = next(f for f in findings if f["rule_id"] == "GEN-TLS-DISABLED")
        assert f["confidence"] == "HIGH"

    def test_yaml_unsafe_load(self):
        findings, _ = run("conf.py", "Python", "data = yaml.load(stream)")
        assert any(f["rule_id"] == "PY-UNSAFE-YAML" for f in findings)

    def test_yaml_safe_load_not_flagged(self):
        findings, _ = run("conf.py", "Python",
                          "data = yaml.load(stream, Loader=yaml.SafeLoader)")
        assert not any(f["rule_id"] == "PY-UNSAFE-YAML" for f in findings)

    def test_innerhtml_xss(self):
        findings, _ = run("ui.ts", "TypeScript", 'el.innerHTML = userInput;')
        f = next(f for f in findings if f["rule_id"] == "JS-INNERHTML")
        assert f["category"] == "xss"

    def test_django_debug_true(self):
        findings, _ = run("settings.py", "Python", "DEBUG = True\n")
        assert any(f["rule_id"] == "DJANGO-DEBUG-TRUE" and
                   f["confidence"] == "HIGH" for f in findings)

    def test_env_committed_tree_level(self):
        assert detect_committed_env_files([".env", ".env.example", "src/.env.local"]) == [".env", "src/.env.local"]

    def test_ssrf_pattern(self):
        findings, _ = run("fetcher.py", "Python",
                          "r = requests.get(request.args.get('url'))")
        assert any(f["rule_id"] == "PY-SSRF-REQUEST-ARGS" for f in findings)


class TestSafeCases:
    def test_safe_code_produces_no_findings(self):
        safe = (
            "import subprocess\n"
            "def ls(d):\n"
            "    return subprocess.run(['ls', d], shell=False)\n"
            "data = yaml.safe_load(open('cfg.yml'))\n"
            "url = 'https://api.internal/health'\n"
        )
        findings, executed = run("safe.py", "Python", safe)
        assert findings == []
        # checks still count as EXECUTED (they ran and passed)
        assert len(executed) > 0

    def test_parameterized_sql_not_flagged(self):
        findings, _ = run("db.py", "Python",
                          'cur.execute("SELECT * FROM users WHERE id=?", (uid,))')
        assert not any(f["rule_id"] == "PY-SQL-FSTRING" for f in findings)

    def test_localhost_http_allowed(self):
        findings, _ = run("dev.js", "JavaScript",
                          "const url = 'http://localhost:3000/dev';")
        assert not any(f["rule_id"] == "GEN-INSECURE-HTTP" for f in findings)


class TestFindingShape:
    def test_all_fields_present(self):
        findings, _ = run("s.py", "Python", 'subprocess.run(cmd, shell=True)')
        f = findings[0]
        for field in ("rule_id", "title", "severity", "confidence", "file",
                      "line", "symbol", "evidence", "why", "recommendation",
                      "standards", "detection_method", "fingerprint"):
            assert field in f

    def test_fingerprints_stable_and_distinct(self):
        code = 'subprocess.run(a, shell=True)\n\n\n\n\nsubprocess.run(b, shell=True)'
        fa, _ = run("s.py", "Python", code)
        fb, _ = run("s.py", "Python", code)
        ids_a = sorted(f["fingerprint"] for f in fa)
        ids_b = sorted(f["fingerprint"] for f in fb)
        assert ids_a == ids_b            # stable across scans
        assert len(ids_a) >= 2           # distinct lines kept separate


class TestStandardsMappings:
    def test_known_mappings_are_exact(self):
        _, executed = run("s.py", "Python", 'subprocess.run(a, shell=True)')
        findings, _ = run("s.py", "Python", 'subprocess.run(a, shell=True)')
        f = findings[0]
        for s in f["standards"]:
            assert s["standard"] in {"OWASP Top 10:2021", "OWASP ASVS 4.0"}
            if s["standard"] == "OWASP Top 10:2021":
                assert s["id"].startswith("A") and len(s["id"]) == 3

    def test_no_invented_standard_ids(self):
        allowed_top10 = {f"A{str(i).zfill(2)}" for i in range(1, 11)}
        for rule in RULES:
            for s in rule.standards:
                if s["standard"] == "OWASP Top 10:2021":
                    assert s["id"] in allowed_top10, rule.id
