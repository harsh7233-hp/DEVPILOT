"""Deep analysis scan orchestrator.

Runs once per repository snapshot and feeds every Module-2 engine from a
single file fetch:

    1. Fetch file tree + contents (same filtering rules as intelligence scan)
    2. Extract per-file symbols (function/class spans) for context
    3. Security rules engine      → evidence-based findings
    4. Secret detection           → masked-only findings
    5. Performance engine         → potential issues (static)
    6. Code metrics               → CC, sizes, duplication, docs, smells
    7. Dependency scanner         → manifests + live OSV.dev lookup
    8. Scoring                    → posture, health cards, coverage
    9. Persist report             → data/security/{rid}.json

The persisted report stores MASKED secret previews and redacted evidence
only — raw secrets never reach disk through this module.
"""

from __future__ import annotations

import asyncio
import hashlib
import time
from typing import Any, Dict, List, Tuple

from app.services.analysis import detect_language, filter_files
from app.services.code_metrics import (
    compute_code_health,
    extract_functions,
    reliability_pattern_counts,
)
from app.services.deps_scanner import parse_manifests, scan_dependencies
from app.services.findings_store import apply_statuses, save_security_report
from app.services.github import get_file_content, get_file_tree
from app.services.intelligence import (
    MAX_ANALYSIS_BYTES,
    MAX_CONTENT_FILES,
    TEST_FILE_RE,
    _parse_python,
    repo_id,
)
from app.services.performance_engine import scan_file_performance
from app.services.priority_engine import compute_priority
from app.services.secrets_detector import scan_files_for_secrets
from app.services.security_rules import (
    detect_committed_env_files,
    env_committed_finding,
    scan_file_security,
)
from app.services.security_scoring import compute_security_posture

SCAN_STAGES = [
    "Fetching Files",
    "Parsing Symbols",
    "Running Security Rules",
    "Detecting Secrets",
    "Analyzing Performance Patterns",
    "Scanning Dependencies",
    "Computing Scores",
]

MANIFEST_NAMES = ("package.json", "requirements.txt", "pyproject.toml")
CODE_LANGS = {
    "TypeScript", "JavaScript", "Python", "Java", "Kotlin", "Scala", "Go",
    "Rust", "Ruby", "PHP", "C#", "Swift", "C", "C++",
}

# Files whose content is scanned by the security engines.
SCANNABLE_LANGS = {"TypeScript", "JavaScript", "Python"}


class DeepScanJob:
    def __init__(self, owner: str, repo: str, branch: str) -> None:
        self.id = f"deep-{int(time.time() * 1000)}-{owner}/{repo}".replace("/", "-")
        self.owner = owner
        self.repo = repo
        self.branch = branch
        self.status = "pending"
        self.progress = 0.0
        self.stage = 0
        self.message = SCAN_STAGES[0]
        self.error = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "owner": self.owner, "repo": self.repo,
            "branch": self.branch, "status": self.status,
            "progress": round(self.progress, 3), "stage": self.stage,
            "message": self.message, "stages": SCAN_STAGES, "error": self.error,
        }


_deep_jobs: Dict[str, DeepScanJob] = {}


def create_deep_job(owner: str, repo: str, branch: str) -> DeepScanJob:
    job = DeepScanJob(owner, repo, branch)
    _deep_jobs[job.id] = job
    return job


def get_deep_job(job_id: str) -> DeepScanJob | None:
    return _deep_jobs.get(job_id)


def _set_stage(job: DeepScanJob, stage: int, progress: float) -> None:
    job.stage = stage
    job.progress = min(progress, 0.99)
    job.message = SCAN_STAGES[stage] if stage < len(SCAN_STAGES) else job.message


async def _fetch_all(token: str, owner: str, repo: str, ref: str,
                     paths: List[str]) -> Dict[str, str]:
    sem = asyncio.Semaphore(12)
    contents: Dict[str, str] = {}

    async def fetch(path: str) -> None:
        async with sem:
            try:
                text = await get_file_content(token, owner, repo, path, ref)
                if text is not None:
                    contents[path] = text
            except Exception:
                pass

    await asyncio.gather(*(fetch(p) for p in paths))
    return contents


async def run_deep_scan(job_id: str, token: str) -> None:
    job = _deep_jobs.get(job_id)
    if not job:
        return
    rid = repo_id(job.owner, job.repo)

    try:
        # ── Stage 0: fetch ────────────────────────────────────────────
        _set_stage(job, 0, 0.05)
        tree = await get_file_tree(token, job.owner, job.repo, job.branch)
        blobs = [t for t in tree if t.get("type") == "blob"]
        if not blobs:
            raise RuntimeError("Repository is empty or inaccessible")

        filtered = filter_files(tree)
        code_items = [
            f for f in filtered
            if detect_language(f["path"]) in SCANNABLE_LANGS
        ]
        code_items.sort(key=lambda f: -(f.get("size") or 0))
        code_items = [f for f in code_items if (f.get("size") or 0) <= MAX_ANALYSIS_BYTES]
        scanned_items = code_items[:MAX_CONTENT_FILES]
        total_code_in_tree = len(code_items)

        contents = await _fetch_all(token, job.owner, job.repo, job.branch,
                                    [i["path"] for i in scanned_items])

        env_paths = detect_committed_env_files([b["path"] for b in blobs])
        manifest_items = [b for b in blobs if b["path"].rsplit("/", 1)[-1] in MANIFEST_NAMES]
        lockfile_names = ("package-lock.json", "yarn.lock", "pnpm-lock.yaml",
                          "poetry.lock", "Pipfile.lock", "Cargo.lock", "composer.lock")
        has_lockfile = any(b["path"].rsplit("/", 1)[-1] in lockfile_names for b in blobs)
        manifest_contents = await _fetch_all(
            token, job.owner, job.repo, job.branch,
            [b["path"] for b in manifest_items[:6]],
        )

        # ── Stage 1-4: per-file engines ───────────────────────────────
        security_findings: List[Dict[str, Any]] = []
        executed_rule_ids: List[str] = []
        secret_findings: List[Dict[str, Any]] = []
        perf_findings: List[Dict[str, Any]] = []
        all_funcs: List[Any] = []
        langs_by_path: Dict[str, str] = {}
        source_files = test_files = 0

        total = max(1, len(contents))
        for idx, (path, content) in enumerate(contents.items()):
            lang = detect_language(path) or ""
            langs_by_path[path] = lang
            if TEST_FILE_RE.search(path):
                test_files += 1
            else:
                source_files += 1

            # symbol spans for enclosing-function attribution
            syms: List[Tuple[int, int, str]] = []
            funcs_any = []
            if lang == "Python":
                parsed = _parse_python(content, path)
                for fn in parsed["functions"]:
                    syms.append((fn["start_line"], fn["end_line"], f"{fn['name']}()"))
                for cl in parsed["classes"]:
                    syms.append((cl["start_line"], cl["end_line"], f"class {cl['name']}"))
                pyfuncs, _cls = extract_functions(path, lang, content)
                funcs_any = pyfuncs
            elif lang in ("JavaScript", "TypeScript"):
                jsfuncs = extract_functions(path, lang, content)[0]
                for fn in jsfuncs:
                    syms.append((fn.start, fn.end, f"{fn.name}()"))
                funcs_any = jsfuncs

            all_funcs.extend(funcs_any)

            sec, executed = scan_file_security(path, lang, content, syms)
            security_findings.extend(sec)
            executed_rule_ids.extend(executed)
            secret_findings.extend(scan_files_for_secrets({path: content}))
            perf_findings.extend(scan_file_performance(path, lang, content, syms))

            if (idx + 1) % 15 == 0 or idx + 1 == total:
                frac = (idx + 1) / total
                stage = 1 + int(frac * 4)          # stages 1..4
                _set_stage(job, min(stage, 4), 0.10 + 0.55 * frac)
                job.message = f"{SCAN_STAGES[min(stage, 4)]}... {idx + 1}/{total}"

        # committed .env findings (tree-level rule)
        for p in env_paths:
            security_findings.append(env_committed_finding(p))

        # ── Stage 5: dependencies ─────────────────────────────────────
        _set_stage(job, 5, 0.72)
        dep_report = await scan_dependencies(manifest_contents)
        parsed_manifests = parse_manifests(manifest_contents)
        dependency_info = {
            **parsed_manifests,
            "has_lockfile": has_lockfile,
        }

        stats = {
            "source_files": source_files,
            "test_files": test_files,
            "analyzed_files": len(contents),
            "code_files_in_tree": total_code_in_tree,
        }

        reliability_counts = reliability_pattern_counts(contents, langs_by_path)

        # ── Stage 6: scores ───────────────────────────────────────────
        _set_stage(job, 6, 0.88)
        health = compute_code_health(all_funcs, contents, langs_by_path,
                                     stats, reliability_counts, dependency_info)

        perf_count = len(perf_findings)
        loc_total = sum(len(c.splitlines()) for c in contents.values())
        perf_density_per_kloc = (perf_count * 1000.0 / loc_total) if loc_total else 0.0
        perf_score = None
        if loc_total:
            perf_score = max(0, min(100, round(100 - perf_density_per_kloc * 40)))

        from app.services.findings_store import load_security_report
        prev_report = load_security_report(rid)
        statuses = (prev_report or {}).get("status_overrides", {})

        all_findings = security_findings + secret_findings + perf_findings
        all_findings = apply_statuses(all_findings, statuses)

        posture = compute_security_posture(executed_rule_ids, all_findings, statuses)

        coverage = build_coverage(
            analyzed=len(contents),
            code_in_tree=total_code_in_tree,
            dep_status=dep_report["status"],
            secrets_run=True,
            config_rules_executed=len(set(executed_rule_ids)),
            manual_review_open=sum(
                1 for f in all_findings
                if f.get("manual_review_required") and f.get("status") == "open"
            ),
        )

        dependents_map = await _graph_dependents(rid)

        priority_queue = compute_priority(
            [f for f in all_findings if f.get("status") in (None, "open")],
            dependents_map,
        )

        report = {
            "owner": job.owner,
            "repo": job.repo,
            "branch": job.branch,
            "generated_at": int(time.time()),
            "analysis_kind": "STATIC ANALYSIS",
            "disclaimer": (
                "Automated security analysis may not detect all vulnerabilities. "
                "Results are indicative and do not guarantee complete security. "
                "All findings are static pattern detections on the analyzed "
                "snapshot. No runtime profiling was performed; no measured "
                "timings are reported."
            ),
            "stats": stats,
            "posture": posture,
            "health_cards": build_health_cards(health, posture, perf_score, stats),
            "findings": all_findings[:500],
            "secrets": [f for f in secret_findings],   # masked previews only
            "performance_issues": perf_findings[:300],
            "dependencies": dep_report,
            "coverage": coverage,
            "priority_queue": priority_queue[:60],
            "status_overrides": statuses,
            "counts": summarize_counts(security_findings, secret_findings,
                                       perf_findings, statuses),
        }
        save_security_report(rid, report)

        # Emit notifications for significant findings (real events only)
        _emit_scan_notifications(job, report)

        job.status = "completed"
        job.progress = 1.0
        job.message = "Deep analysis complete"
    except Exception as exc:
        job.status = "failed"
        job.error = str(exc)
        job.message = f"Deep scan failed: {exc}"


async def _graph_dependents(rid: str) -> Dict[str, int]:
    """fan-in per file path from the stored graph, when it exists."""
    try:
        from app.services.graph import get_all_relationships
        rels = get_all_relationships(rid)
        fan_in: Dict[str, int] = {}
        for r in rels:
            to_fp = r.get("to_file_path") or (r.get("to_id", "").split(":")[-2] if ":" in r.get("to_id", "") else "")
            if to_fp:
                fan_in[to_fp] = fan_in.get(to_fp, 0) + 1
        return fan_in
    except Exception:
        return {}


def _emit_scan_notifications(job: DeepScanJob, report: Dict[str, Any]) -> None:
    """Create notifications from real scan results. Only real findings trigger notifications."""
    from app.services.notifications import create_notification

    session_id = hashlib.sha256(job.id.encode()).hexdigest()[:16]
    owner = job.owner
    repo = job.repo

    # Security scan completed
    posture = report.get("posture", {})
    open_count = posture.get("open_findings", 0) if posture else 0
    total_count = report.get("counts", {}).get("total_findings", 0)

    create_notification(
        session_id,
        category="security",
        title=f"Security deep scan completed for {owner}/{repo}",
        message=f"{total_count} finding(s) detected, {open_count} open. Security posture: {posture.get('score', 'N/A')}/100.",
        severity="info" if open_count == 0 else ("high" if open_count > 5 else "medium"),
        href="/security",
        entity_type="security_report",
        entity_id=f"{owner}/{repo}",
        owner=owner,
        repo=repo,
    )

    # Notify on high-severity findings
    findings = report.get("findings", [])
    critical_findings = [f for f in findings if f.get("severity") == "CRITICAL" and f.get("status") in (None, "open")]
    high_findings = [f for f in findings if f.get("severity") == "HIGH" and f.get("status") in (None, "open")]

    if critical_findings:
        create_notification(
            session_id,
            category="security",
            title=f"{len(critical_findings)} critical security finding(s) in {owner}/{repo}",
            message=f"Critical: {critical_findings[0].get('title', 'Unknown')}" + (f" and {len(critical_findings) - 1} more" if len(critical_findings) > 1 else ""),
            severity="critical",
            href="/security",
            entity_type="finding",
            entity_id=critical_findings[0].get("fingerprint", ""),
            owner=owner,
            repo=repo,
        )

    if high_findings:
        create_notification(
            session_id,
            category="security",
            title=f"{len(high_findings)} high-severity finding(s) in {owner}/{repo}",
            message=f"HIGH: {high_findings[0].get('title', 'Unknown')}" + (f" and {len(high_findings) - 1} more" if len(high_findings) > 1 else ""),
            severity="high",
            href="/security",
            entity_type="finding",
            entity_id=high_findings[0].get("fingerprint", ""),
            owner=owner,
            repo=repo,
        )

    # Secret detection
    secrets = report.get("secrets", [])
    if secrets:
        create_notification(
            session_id,
            category="security",
            title=f"{len(secrets)} secret(s) detected in {owner}/{repo}",
            message="Potential secrets found in source code. Review masked previews in the security report.",
            severity="high",
            href="/security",
            entity_type="secrets",
            entity_id=f"{owner}/{repo}",
            owner=owner,
            repo=repo,
        )

    # Dependency vulnerabilities
    deps = report.get("dependencies", {})
    vulns = deps.get("vulnerabilities", [])
    if vulns:
        create_notification(
            session_id,
            category="dependency",
            title=f"{len(vulns)} dependency vulnerability/vulnerabilities in {owner}/{repo}",
            message=f"OSV.dev found {len(vulns)} known vulnerabilities in dependencies.",
            severity="high",
            href="/security",
            entity_type="dependencies",
            entity_id=f"{owner}/{repo}",
            owner=owner,
            repo=repo,
        )

    # Performance issues
    perf = report.get("performance_issues", [])
    if len(perf) > 0:
        create_notification(
            session_id,
            category="performance",
            title=f"{len(perf)} performance pattern(s) detected in {owner}/{repo}",
            message="Static analysis detected potential performance issues.",
            severity="medium",
            href="/security",
            entity_type="performance",
            entity_id=f"{owner}/{repo}",
            owner=owner,
            repo=repo,
        )


COVERAGE_SECTIONS = ["static_analysis", "dependency_analysis", "secret_detection",
                     "configuration_analysis", "asvs_checks", "manual_review"]


def build_coverage(analyzed: int, code_in_tree: int, dep_status: str,
                   secrets_run: bool, config_rules_executed: int,
                   manual_review_open: int) -> Dict[str, Any]:
    share = (analyzed / code_in_tree) if code_in_tree else 0.0
    static_state = "completed" if share >= 0.8 else ("partial" if share > 0 else "not_analyzed")
    return {
        "static_analysis": {
            "state": static_state,
            "detail": f"{analyzed} of {code_in_tree} scannable code files analyzed",
            "share": round(share, 3),
        },
        "dependency_analysis": {
            "state": {"completed": "completed", "partial_analysis": "partial",
                      "not_analyzed": "not_analyzed"}.get(dep_status, "not_analyzed"),
            "detail": "Live OSV.dev query of pinned manifest versions",
        },
        "secret_detection": {
            "state": "completed" if secrets_run else "not_analyzed",
            "detail": "Pattern + entropy scanning of analyzed files; previews masked",
        },
        "configuration_analysis": {
            "state": "completed" if config_rules_executed > 0 else "not_analyzed",
            "detail": f"{config_rules_executed} configuration-relevant rules executed",
        },
        "asvs_checks": {
            "state": "partial",
            "detail": ("Automated checks cover a subset of OWASP ASVS chapters "
                       "(V2, V4, V5, V6, V7, V9, V14). Full ASVS verification "
                       "requires manual assessment."),
        },
        "manual_review": {
            "state": "completed" if manual_review_open == 0 else "partial",
            "detail": f"{manual_review_open} open finding(s) flagged as requiring manual review",
        },
    }


def build_health_cards(health: Dict[str, Any], posture: Optional[Dict[str, Any]],
                       perf_score: Optional[int], stats: Dict[str, Any]) -> Dict[str, Any]:
    """Assemble the six overview cards with formulas + factor transparency."""
    factor_by_key = {f["key"]: f for f in health["factors"]}
    tests_factor = factor_by_key.get("tests")

    cards = {
        "code_health": {
            "title": "Code Health",
            "score": health["overall"],
            "formula": health["formulas"]["code_health"],
            "methodology": health["methodology"],
            "factors": [
                {"name": f["key"], "score": f["score"], "weight": f["weight"],
                 "available": f["available"], "measurements": f["measurements"],
                 "formula": f["formula"]}
                for f in health["factors"]
            ],
        },
        "reliability": {
            "title": "Reliability",
            "score": (factor_by_key.get("reliability") or {}).get("score"),
            "formula": health["formulas"]["reliability"],
            "methodology": "Static error-handling evidence only. This is not a "
                           "measured/observed production reliability metric.",
            "measurements": (factor_by_key.get("reliability") or {}).get("measurements"),
        },
        "maintainability": {
            "title": "Maintainability",
            "score": (factor_by_key.get("maintainability") or {}).get("score"),
            "formula": health["formulas"]["maintainability"],
            "methodology": "Composite of measured function/file sizes.",
            "measurements": (factor_by_key.get("maintainability") or {}).get("measurements"),
            "smells": health.get("smells"),
        },
        "security_posture": {
            "title": "Security Posture",
            "score": posture["score"] if posture else None,
            "unavailable_reason": None if posture else "No security checks were executable",
            "formula": posture["formula"] if posture else None,
            "methodology": "Evidence-based score derived from the security checks "
                           "DevPilot was able to perform.",
            "details": posture,
        },
        "performance": {
            "title": "Performance",
            "score": perf_score,
            "analysis_kind": "STATIC ANALYSIS",
            "formula": health["formulas"]["performance_card"],
            "methodology": "Density of statically detected potential performance "
                           "issues. MEASURED PERFORMANCE is not available — no "
                           "profiler data exists.",
        },
        "test_coverage": {
            "title": "Test Coverage",
            "score": tests_factor.get("score") if tests_factor else None,
            "is_proxy": True,
            "proxy_label": "Static file-share proxy",
            "formula": health["formulas"]["tests"],
            "methodology": "Derived from test vs source file counts. Runtime line/branch "
                           "coverage requires executing the test suite with instrumentation, "
                           "which DevPilot does not do.",
            "measurements": (tests_factor or {}).get("measurements"),
        },
    }
    return cards


def summarize_counts(security: List[Dict[str, Any]], secrets: List[Dict[str, Any]],
                     perf: List[Dict[str, Any]],
                     overrides: Dict[str, Dict[str, Any]]) -> Dict[str, int]:
    def sev_count(items: List[Dict[str, Any]], status_filter_open: bool = False) -> Dict[str, int]:
        out = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for f in items:
            if status_filter_open:
                st = overrides.get(f.get("fingerprint", ""), {}).get("status", "open")
                if st != "open":
                    continue
            out[f.get("severity", "LOW")] = out.get(f.get("severity", "LOW"), 0) + 1
        return out

    return {
        "security": sev_count(security),
        "secrets": len(secrets),
        "performance": sev_count(perf),
        "total_findings": len(security) + len(secrets) + len(perf),
    }
