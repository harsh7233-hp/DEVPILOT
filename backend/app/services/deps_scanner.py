"""Dependency manifest parsing + vulnerability lookup via OSV.dev.

Data sources:
- package.json / requirements.txt / pyproject.toml / poetry dependencies
  parsed from actual repository content.
- Vulnerability data queried live from https://api.osv.dev/v1/querybatch.
  We ONLY report what OSV returns. If the network call fails or returns
  nothing, the section is marked ``not_analyzed`` with a reason. CVE/GHSA IDs,
  affected ranges and fixed versions are passed through verbatim — never
  synthesized.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

import httpx

OSV_QUERYBATCH_URL = "https://api.osv.dev/v1/querybatch"
OSV_VULN_URL = "https://api.osv.dev/v1/vulns/{id}"
OSV_TIMEOUT = 20.0

_ECOSYSTEM_MAP = {
    # manifest marker → (osv ecosystem name)
    "package.json": "npm",
    "requirements.txt": "PyPI",
    "pyproject.toml": "PyPI",
}

_VERSION_CLEAN_RE = re.compile(r"^[^0-9]*([0-9][0-9A-Za-z.\-+_]*)")


def _clean_version(spec: str) -> Optional[str]:
    m = _VERSION_CLEAN_RE.match(spec.strip())
    return m.group(1) if m else None


def parse_manifests(manifests: Dict[str, str]) -> Dict[str, Any]:
    """Parse manifest contents → {packages: [{name, version, ecosystem, source}],
    direct_dependencies count, has_lockfile info handled by caller}."""
    packages: List[Dict[str, Any]] = []

    for path, content in manifests.items():
        base = path.rsplit("/", 1)[-1]
        try:
            if base == "package.json":
                data = json.loads(content)
                for section in ("dependencies", "devDependencies"):
                    for name, spec in (data.get(section) or {}).items():
                        version = _clean_version(str(spec))
                        packages.append({
                            "name": name,
                            "version": version,
                            "raw_spec": str(spec),
                            "ecosystem": "npm",
                            "source": path,
                            "dev": section == "devDependencies",
                        })
            elif base == "requirements.txt":
                for line in content.splitlines():
                    line = line.split("#", 1)[0].strip()
                    if not line or line.startswith("-"):
                        continue
                    name_part = re.split(r"[=<>!~\[\s;]", line, 1)[0].strip()
                    vm = re.search(r"(?:==|>=|~=)\s*([0-9][^\s,;]+)", line)
                    if not name_part:
                        continue
                    packages.append({
                        "name": name_part,
                        "version": vm.group(1) if vm else None,
                        "raw_spec": line,
                        "ecosystem": "PyPI",
                        "source": path,
                        "dev": False,
                    })
            elif base == "pyproject.toml":
                deps = _parse_pyproject_deps(content)
                for name, spec in deps:
                    version = _clean_version(spec) if spec else None
                    packages.append({
                        "name": name,
                        "version": version,
                        "raw_spec": spec or "",
                        "ecosystem": "PyPI",
                        "source": path,
                        "dev": False,
                    })
        except Exception:
            continue

    return {
        "packages": packages,
        "direct_dependencies": len([p for p in packages if not p.get("dev")]),
        "has_manifest": len(packages) > 0,
    }


def _parse_pyproject_deps(content: str) -> List[Tuple[str, str]]:
    """Minimal TOML-ish extraction of PEP 621 [project] dependencies and
    Poetry [tool.poetry.dependencies]. Not a full TOML parser by design."""
    results: List[Tuple[str, str]] = []
    in_project_deps = False
    in_poetry_deps = False
    for raw in content.splitlines():
        line = raw.strip()
        if line.startswith("["):
            in_project_deps = line == "[project]"
            nxt = line.startswith("[project.optional-dependencies")
            in_poetry_deps = line == "[tool.poetry.dependencies]"
            if not in_project_deps and not nxt:
                in_project_deps = False
            continue
        if "=" not in line or line.startswith("#"):
            continue
        name, _, value = line.partition("=")
        name = name.strip().strip('"').strip("'")
        value = value.strip().strip('"').strip("'").rstrip(",")
        if in_poetry_deps:
            results.append((name, value))
        elif in_project_deps and name == "dependencies" and value.startswith("["):
            for m in re.finditer(r'"([^"]+)"', value):
                dep = m.group(1)
                dep_name = re.split(r"[=<>!~\[;\s]", dep, 1)[0].strip()
                vm = re.search(r"(?:==|>=|~=)\s*([0-9][^\s,\"]+)", dep)
                results.append((dep_name, vm.group(1) if vm else ""))
    return results


# ── OSV integration ──────────────────────────────────────────────────

def build_osv_queries(packages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    queries = []
    for p in packages:
        if p.get("version"):
            queries.append({
                "package": {"name": p["name"], "ecosystem": p["ecosystem"]},
                "version": p["version"],
                "_pkg": p,
            })
    return queries


def parse_osv_batch_response(resp_json: Dict[str, Any],
                             queries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Map OSV querybatch results to per-package vulnerability records.

    Only fields returned by OSV are surfaced. Severity uses OSV's
    ``database_specific.severity`` when present; otherwise ``UNKNOWN``
    (displayed as such — we do not guess).
    """
    vulns_out: List[Dict[str, Any]] = []
    results = resp_json.get("results", [])
    for q, res in zip(queries, results):
        pkg = q["_pkg"]
        for v in (res or {}).get("vulns", []) or []:
            sev = None
            db_spec = v.get("database_specific") or {}
            raw_sev = db_spec.get("severity")
            if isinstance(raw_sev, str) and raw_sev.upper() in {
                "CRITICAL", "HIGH", "MODERATE", "MEDIUM", "LOW"
            }:
                sev = {"MODERATE": "MEDIUM"}.get(raw_sev.upper(), raw_sev.upper())
            fixed = None
            affected_range = None
            for aff in v.get("affected", []):
                if aff.get("package", {}).get("name") != pkg["name"]:
                    continue
                for rng in aff.get("ranges", []) or []:
                    events = rng.get("events", []) or []
                    introduced = next((e.get("introduced") for e in events if "introduced" in e), None)
                    fix = next((e.get("fixed") for e in events if "fixed" in e), None)
                    if introduced:
                        affected_range = f">= {introduced}" + (f", < {fix}" if fix else "")
                    if fix and not fixed:
                        fixed = fix
            aliases = [a for a in v.get("aliases", []) if a] or [v.get("id", "")]
            vulns_out.append({
                "package": pkg["name"],
                "installed_version": pkg["version"],
                "ecosystem": pkg["ecosystem"],
                "vulnerability_id": v.get("id", ""),
                "aliases": aliases[:4],
                "summary": (v.get("summary") or v.get("details") or "")[:300],
                "severity": sev or "UNKNOWN",
                "affected_versions": affected_range,
                "recommended_version": fixed,
                "fixed_version_available": bool(fixed),
                "source": "OSV.dev",
                "manifest_source": pkg["source"],
            })
    return vulns_out


async def scan_dependencies(manifests: Dict[str, str]) -> Dict[str, Any]:
    """Full dependency analysis. Network failures degrade gracefully."""
    parsed = parse_manifests(manifests)
    result: Dict[str, Any] = {
        **parsed,
        "status": "not_analyzed",
        "reason": None,
        "vulnerabilities": [],
        "source": None,
    }
    queries = build_osv_queries(parsed["packages"])
    pinned = [q for q in queries]
    if not pinned:
        result["status"] = "partial_analysis"
        result["reason"] = (
            "Manifests found but no pinned versions — cannot match against "
            "the vulnerability database without exact versions."
        )
        return result

    payload = {"queries": [
        {"package": q["package"], "version": q["version"]} for q in queries
    ]}
    try:
        async with httpx.AsyncClient(timeout=OSV_TIMEOUT) as client:
            resp = await client.post(OSV_QUERYBATCH_URL, json=payload,
                                     headers={"Content-Type": "application/json"})
        if resp.status_code != 200:
            result["status"] = "not_analyzed"
            result["reason"] = f"Vulnerability database unavailable (HTTP {resp.status_code})"
            return result
        vulns = parse_osv_batch_response(resp.json(), queries)
        result["vulnerabilities"] = vulns
        result["status"] = "completed"
        result["source"] = "OSV.dev live query at scan time"
        return result
    except Exception as exc:
        result["status"] = "not_analyzed"
        result["reason"] = f"Vulnerability database unreachable: {exc.__class__.__name__}"
        return result
