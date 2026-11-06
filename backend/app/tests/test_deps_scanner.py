"""Dependency scanner tests: manifest parsing and OSV batch response handling."""

from app.services.deps_scanner import (
    build_osv_queries,
    parse_manifests,
    parse_osv_batch_response,
)


class TestManifestParsing:
    def test_package_json(self):
        m = parse_manifests({
            "package.json": '{"dependencies": {"react": "^18.2.0"}, "devDependencies": {"vitest": "^1.0.0"}}'
        })
        names = {p["name"] for p in m["packages"]}
        assert "react" in names
        assert "vitest" in names
        assert m["has_lockfile"] is False
        react = next(p for p in m["packages"] if p["name"] == "react")
        assert react["ecosystem"] == "npm"
        assert react["dev"] is False
        vit = next(p for p in m["packages"] if p["name"] == "vitest")
        assert vit["dev"] is True

    def test_requirements_txt(self):
        m = parse_manifests({
            "requirements.txt": "flask==3.0.0\nrequests>=2.28\n# comment\n"
        })
        assert len(m["packages"]) == 2
        assert m["ecosystem"] == "PyPI"
        flask = next(p for p in m["packages"] if p["name"] == "flask")
        assert flask["version"] == "3.0.0"

    def test_pyproject_toml(self):
        content = '[project]\nname="devpilot"\ndependencies=["fastapi>=0.100","uvicorn"]\n'
        m = parse_manifests({"pyproject.toml": content})
        assert len(m["packages"]) == 2
        assert m["ecosystem"] == "PyPI"

    def test_empty_manifest(self):
        m = parse_manifests({})
        assert m["packages"] == []
        assert m["total"] == 0

    def test_lockfile_detected(self):
        m = parse_manifests({
            "package.json": "{}",
            "package-lock.json": "{}"
        })
        assert m["has_lockfile"] is True

    def test_invalid_json_graceful(self):
        m = parse_manifests({"package.json": "NOT JSON"})
        assert m["packages"] == []


class TestOSVBatchResponse:
    def test_parsing_simple(self):
        queries = [
            {"package": {"name": "react", "ecosystem": "npm"}, "version": "18.1.0"},
            {"package": {"name": "flask", "ecosystem": "PyPI"}, "version": "2.0.0"},
        ]
        resp = {
            "results": [
                {"vulns": [{"id": "GHSA-1", "summary": "XSS",
                            "database_specific": {"severity": "HIGH"},
                            "affected": [{"package": {"name": "react"},
                                         "ranges": [{"type": "ECOSYSTEM",
                                                     "events": [{"introduced": "<18.0.0"},
                                                                {"fixed": "18.0.1"}]}]}]}]},
                {"vulns": None}
            ]
        }
        vulns = parse_osv_batch_response(resp, queries)
        assert len(vulns) == 1
        assert vulns[0]["vulnerability_id"] == "GHSA-1"
        assert vulns[0]["severity"] == "HIGH"
        assert vulns[0]["package"] == "react"
        assert vulns[0]["ecosystem"] == "npm"
        assert vulns[0]["recommended_version"] == "18.0.1"

    def test_empty_response(self):
        vulns = parse_osv_batch_response({"results": []}, [])
        assert vulns == []

    def test_severity_normalization(self):
        queries = [{"package": {"name": "x", "ecosystem": "npm"}, "version": "1.0.0"}]
        resp = {"results": [{"vulns": [
            {"id": "V1", "summary": "crit", "database_specific": {"severity": "CRITICAL"}, "affected": []},
            {"id": "V2", "summary": "mod", "database_specific": {"severity": "MODERATE"}, "affected": []},
            {"id": "V3", "summary": "low", "database_specific": {"severity": "LOW"}, "affected": []},
            {"id": "V4", "summary": "info", "affected": []},
        ]}]}
        vulns = parse_osv_batch_response(resp, queries)
        severities = {v["vulnerability_id"]: v["severity"] for v in vulns}
        assert severities["V1"] == "CRITICAL"
        assert severities["V2"] == "MEDIUM"
        assert severities["V3"] == "LOW"
        assert severities["V4"] == "INFO"


class TestOSVQueries:
    def test_build_queries_deduped(self):
        pkgs = [
            {"name": "react", "version": "18.2.0", "ecosystem": "npm"},
            {"name": "react", "version": "18.2.0", "ecosystem": "npm"},
            {"name": "flask", "version": "3.0.0", "ecosystem": "PyPI"},
        ]
        queries = build_osv_queries(pkgs)
        assert len(queries) == 2

    def test_empty_packages(self):
        assert build_osv_queries([]) == []
