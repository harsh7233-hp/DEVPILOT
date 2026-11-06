"""Code Intelligence scan engine.

Runs a static-analysis pass over a repository and produces:
- repository statistics (files, LOC, languages, entities, dependencies, tests)
- code health & reliability issues + scores
- potential performance issues
- prioritized recommended changes

All scores/findings derive from actual repository content via deterministic
static rules. AI (Groq) is layered on top at the API layer for explanations
and suggested diffs — never for inventing metrics.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.analyzer.base import analyze_file
from app.services.analysis import detect_language, filter_files, should_ignore_path
from app.services.github import (
    get_commits_count,
    get_contributors_count,
    get_file_content,
    get_file_tree,
)

_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
_INTEL_DIR = os.path.join(_DATA_DIR, "intelligence")

SCAN_STAGES = [
    "Scanning Repository",
    "Analyzing Files",
    "Detecting Functions & Classes",
    "Analyzing Dependencies",
    "Checking Pipelines",
    "Checking Performance",
    "Calculating Code Health",
    "Generating Recommendations",
]

CODE_LANGS = {
    "TypeScript", "JavaScript", "Python", "Java", "Kotlin", "Scala", "Go",
    "Rust", "Ruby", "PHP", "C#", "Swift", "C", "C++",
}
TEST_FILE_RE = re.compile(r"(^|/)(tests?|__tests__|spec)(/|$)|(^|/)(test|spec)[^.]*\.[a-z]+$|\.(test|spec)\.[tj]sx?$|_test\.py$|_test\.go$")

MAX_CONTENT_FILES = 400          # cap downloads per scan
MAX_ANALYSIS_BYTES = 120_000     # skip huge files from rule scanning

SEV_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}


def repo_id(owner: str, repo: str) -> str:
    return hashlib.sha256(f"{owner}/{repo}".encode()).hexdigest()[:16]


# ── Job management ────────────────────────────────────────────────

class IntelligenceJob:
    def __init__(self, owner: str, repo: str, branch: str) -> None:
        self.id = str(uuid.uuid4())
        self.owner = owner
        self.repo = repo
        self.branch = branch
        self.status = "pending"
        self.progress = 0.0
        self.stage = 0
        self.message = SCAN_STAGES[0]
        self.error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "owner": self.owner,
            "repo": self.repo,
            "branch": self.branch,
            "status": self.status,
            "progress": round(self.progress, 3),
            "stage": self.stage,
            "message": self.message,
            "stages": SCAN_STAGES,
            "error": self.error,
        }


_intel_jobs: Dict[str, IntelligenceJob] = {}


def create_intel_job(owner: str, repo: str, branch: str) -> IntelligenceJob:
    job = IntelligenceJob(owner, repo, branch)
    _intel_jobs[job.id] = job
    return job


def get_intel_job(job_id: str) -> Optional[IntelligenceJob]:
    return _intel_jobs.get(job_id)


def _set_stage(job: IntelligenceJob, stage: int, progress: float) -> None:
    job.stage = stage
    job.progress = min(progress, 0.99)
    job.message = SCAN_STAGES[stage] if stage < len(SCAN_STAGES) else job.message


# ── Findings model ────────────────────────────────────────────────

def _finding(
    category: str,
    severity: str,
    file_path: str,
    symbol: str,
    line: int,
    problem: str,
    evidence: str,
    explanation: str,
    recommendation: str,
) -> Dict[str, Any]:
    return {
        "id": hashlib.sha1(f"{file_path}:{line}:{problem}".encode()).hexdigest()[:12],
        "category": category,          # health | security | performance
        "severity": severity,          # CRITICAL | HIGH | MEDIUM | LOW
        "file": file_path,
        "symbol": symbol,
        "line": line,
        "problem": problem,
        "evidence": evidence[:400],
        "explanation": explanation,
        "recommendation": recommendation,
        "source": "static-analysis",
    }


def _snippet(lines: List[str], idx: int, span: int = 2) -> str:
    lo = max(0, idx - span)
    hi = min(len(lines), idx + span + 1)
    return "\n".join(lines[lo:hi])


# ── Rule definitions (regex-based static checks) ──────────────────

SECRET_RE = re.compile(
    r"\b(api[_-]?key|apikey|secret[_-]?key?|auth[_-]?token|access[_-]?token|password|passwd|pwd)"
    r"""['\"]?\s*[:=]\s*['\"]([A-Za-z0-9_\-/+=.]{10,})['\"]""",
    re.IGNORECASE,
)
_SECRET_PLACEHOLDER = re.compile(
    r"your[_-]?|example|changeme|change_me|placeholder|xxx+|dummy|sample|<[^>]+>|\$\{|\{\{",
    re.IGNORECASE,
)

HEALTH_RULES_JS = [
    (re.compile(r"\beval\s*\("), "CRITICAL", "Use of eval()",
     "eval() executes arbitrary strings as code, enabling injection attacks and breaking optimizations.",
     "Remove eval(); parse data explicitly or use JSON.parse / safer alternatives."),
    (re.compile(r"catch\s*\([^)]*\)\s*\{\s*\}"), "HIGH", "Empty catch block swallows errors",
     "Silently discarding errors hides failures and makes debugging production incidents very hard.",
     "Log the error, wrap it in a domain-specific error, or rethrow after cleanup."),
    (re.compile(r"catch\s*\{\s*\}"), "MEDIUM", "Empty catch block",
     "An empty catch silently ignores failures.",
     "Handle or log the error explicitly."),
    (re.compile(r"\bdebugger\b"), "MEDIUM", "Debugger statement left in code",
     "debugger statements pause execution in devtools and should never reach production.",
     "Delete the debugger statement."),
    (re.compile(r"\.innerHTML\s*="), "HIGH", "Assignment to innerHTML",
     "Assigning raw HTML can introduce cross-site scripting (XSS) if any part of the string is user-controlled.",
     "Use textContent, or sanitize with DOMPurify before injecting HTML."),
    (re.compile(r"\bany\b\s*[;,)=]|:\s*any\b"), "LOW", "Explicit 'any' type",
     "'any' disables TypeScript's type safety for that value and propagates through call sites.",
     "Replace 'any' with a precise type or 'unknown' plus narrowing."),
]

HEALTH_RULES_PY = [
    (re.compile(r"except\s*:\s*(#.*)?$"), "HIGH", "Bare except swallows errors",
     "A bare except catches SystemExit/KeyboardInterrupt too and hides real errors.",
     "Catch specific exception types and handle or log them."),
    (re.compile(r"except\s+\w+\s*:\s*(pass|#)?\s*$"), "MEDIUM", "Exception silenced without handling",
     "Errors caught only to be ignored make failures invisible.",
     "Log the exception or let it propagate."),
    (re.compile(r"\bexec\s*\("), "CRITICAL", "Use of exec()",
     "exec() runs arbitrary dynamic code, a serious injection risk.",
     "Refactor to avoid dynamic execution; use explicit logic or a safe DSL."),
    (re.compile(r"\bpickle\.loads?\("), "MEDIUM", "Pickle deserialization",
     "Loading pickles from untrusted sources can execute arbitrary code.",
     "Prefer JSON or another safe format for untrusted input."),
    (re.compile(r"assert\s+.*,#?production?", re.IGNORECASE), "LOW", "Assert used for validation",
     "Assertions are stripped under python -O, silently disabling checks.",
     "Raise explicit exceptions for runtime validation."),
]

SHARED_RULES = [
    (re.compile(r"\b(TODO|FIXME|HACK|XXX)\b\b"), "LOW", "Unresolved TODO/FIXME marker"),
    (re.compile(r"console\.(log|debug)\("), "LOW", "Console debug statement"),
    (re.compile(r"\bprint\("), "LOW", "Print statement instead of logger"),
]

PERF_LOOP_RE = re.compile(r"^\s*(for\s*\(|while\s*\(|for\s+\w+\s+in\s|\.forEach\(|\.map\()")
PERF_AWAIT_RE = re.compile(r"\bawait\s+")
PERF_INCLUDES_RE = re.compile(r"\.(includes|indexOf|find|findIndex|some|every)\(")
PERF_DEEP_CLONE_RE = re.compile(r"JSON\.parse\s*\(\s*JSON\.stringify")
PERF_NEWREGEX_RE = re.compile(r"new\s+RegExp\s*\(")
PERF_SYNCIO_RE = re.compile(r"\b(readFileSync|writeFileSync|existsSync|readdirSync|execSync)\b")
PY_PERF_REQUESTS_RE = re.compile(r"\brequests\.(get|post|put|delete|head)\(")
PY_SLEEP_RE = re.compile(r"\btime\.sleep\s*\(")
PY_OPEN_RE = re.compile(r"\bopen\s*\(")
FUNC_DEF_PY_RE = re.compile(r"^(\s*)def\s+(\w+)\s*\(", re.MULTILINE)
CLASS_DEF_PY_RE = re.compile(r"^(\s*)class\s+(\w+)", re.MULTILINE)


# ── Python lightweight parser (tree-sitter covers TS/JS only) ─────

def _parse_python(content: str, path: str) -> Dict[str, Any]:
    lines = content.splitlines()
    functions: List[Dict[str, Any]] = []
    classes: List[Dict[str, Any]] = []

    def line_of(offset: int) -> int:
        return content.count("\n", 0, offset)

    for m in FUNC_DEF_PY_RE.finditer(content):
        start = m.start()
        indent = len(m.group(1))
        end = len(lines) - 1
        for i in range(line_of(start) + 1, len(lines)):
            stripped = lines[i]
            if stripped.strip() and (len(stripped) - len(stripped.lstrip())) <= indent and not stripped.strip().startswith("#"):
                end = i - 1
                break
        functions.append({
            "name": m.group(2), "file_path": path,
            "start_line": line_of(start) + 1, "end_line": end + 1, "kind": "function",
        })

    for m in CLASS_DEF_PY_RE.finditer(content):
        start = m.start()
        indent = len(m.group(1))
        end = len(lines) - 1
        for i in range(line_of(start) + 1, len(lines)):
            stripped = lines[i]
            if stripped.strip() and (len(stripped) - len(stripped.lstrip())) <= indent and not stripped.strip().startswith("#"):
                end = i - 1
                break
        classes.append({
            "name": m.group(2), "file_path": path,
            "start_line": line_of(start) + 1, "end_line": end + 1, "kind": "class",
        })

    imports: List[str] = []
    for m in re.finditer(r"^\s*(?:from\s+([\w.]+)\s+import|import\s+([\w.,\s]+))", content, re.MULTILINE):
        mod = m.group(1) or (m.group(2) or "").split(",")[0].strip().split(" ")[0]
        if mod:
            imports.append(mod.split(".")[0])

    return {"functions": functions, "classes": classes, "imports": imports}


# ── Per-file analysis ─────────────────────────────────────────────

def _enclosing_symbol(symbols: List[Tuple[int, int, str]], line_1based: int) -> str:
    for start, end, name in symbols:
        if start <= line_1based <= end:
            return name
    return ""


def _scan_content_rules(path: str, lang: str, content: str, symbols: List[Tuple[int, int, str]],
                        issues: List[Dict[str, Any]], perf: List[Dict[str, Any]]) -> None:
    lines = content.splitlines()
    n = len(lines)

    def add(category: str, severity: str, line_idx: int, problem: str, explanation: str, rec: str) -> None:
        issues.append(_finding(
            category, severity, path,
            _enclosing_symbol(symbols, line_idx + 1),
            line_idx + 1, problem, _snippet(lines, line_idx), explanation, rec,
        ))

    # ── health / security rules ──
    rules = []
    if lang in ("TypeScript", "JavaScript"):
        rules.extend(HEALTH_RULES_JS)
    elif lang == "Python":
        rules.extend(HEALTH_RULES_PY)
    rules.extend(SHARED_RULES)

    seen_rule_line: Dict[str, int] = {}
    for pattern, severity, problem in [(r[0], r[1], r[2]) for r in rules]:
        for m in pattern.finditer(content):
            idx = content.count("\n", 0, m.start())
            key = f"{problem}:{path}"
            # one report per problem-type per function-ish region (cap noise)
            if key in seen_rule_line and abs(seen_rule_line[key] - idx) < 40:
                continue
            seen_rule_line[key] = idx
            explanation, rec = _explain_health(problem)
            add("health", severity, idx, problem, explanation, rec)

    for m in SECRET_RE.finditer(content):
        candidate = m.group(2)
        if _SECRET_PLACEHOLDER.search(candidate):
            continue
        idx = content.count("\n", 0, m.start())
        add("security", "CRITICAL", idx, "Possible hardcoded secret",
            "Credentials embedded in source leak into git history and package artifacts; anyone with repo access obtains them.",
            "Move the value to an environment variable or secret manager and rotate the exposed credential.")

    http_m = re.search(r"""http://(?!localhost|127\.0\.0\.1|0\.0\.0\.0)""", content)
    if http_m:
        idx = content.count("\n", 0, http_m.start())
        add("security", "LOW", idx, "Insecure HTTP endpoint URL",
            "Plain HTTP transmits data unencrypted; requests can be read or tampered with in transit.",
            "Use https:// endpoints.")

    # ── performance rules (potential, statically detected) ──
    loop_lines = [i for i, l in enumerate(lines) if PERF_LOOP_RE.match(l)]
    nested_reported: set = set()
    for li in loop_lines:
        indent_li = len(lines[li]) - len(lines[li].lstrip())
        for lj in range(li + 1, min(li + 80, n)):
            stripped = lines[lj].strip()
            if not stripped or stripped.startswith(("//", "#", "*", "/*")):
                continue
            indent_lj = len(lines[lj]) - len(lines[lj].lstrip())
            if stripped and indent_lj <= indent_li:
                break
            if PERF_LOOP_RE.match(lines[lj]):
                sym = _enclosing_symbol(symbols, li + 1)
                key = (sym, li)
                if key not in nested_reported:
                    nested_reported.add(key)
                    perf.append(_finding(
                        "performance", "HIGH", path, sym, li + 1,
                        "Nested loops detected",
                        _snippet(lines, li),
                        "Nested iteration multiplies work — O(n²) or worse as inputs grow. This is a static pattern detection, not a measured benchmark.",
                        "Flatten the nesting, use a hash map/dictionary for lookups, or restructure the algorithm to avoid the inner loop.",
                    ))
                break

    for li in loop_lines:
        window_end = min(n, li + 60)
        body_indents = []
        indent_li = len(lines[li]) - len(lines[li].lstrip())
        for lj in range(li + 1, window_end):
            stripped = lines[lj].strip()
            if not stripped or stripped.startswith(("//", "#")):
                continue
            indent_lj = len(lines[lj]) - len(lines[lj].lstrip())
            if stripped and indent_lj <= indent_li:
                break
            body_indents.append(lj)
        body_set = set(body_indents)
        awaits_in_body = [j for j in body_set if PERF_AWAIT_RE.search(lines[j])]
        if awaits_in_body:
            perf.append(_finding(
                "performance", "MEDIUM", path, _enclosing_symbol(symbols, li + 1), li + 1,
                "Sequential awaited calls inside a loop",
                _snippet(lines, awaits_in_body[0]),
                "Each await pauses the loop until the request finishes; total latency grows linearly with iterations (static detection, not a measurement).",
                "Collect promises and resolve them together with Promise.all, or batch the API calls if the backend supports it.",
            ))
        includes_hits = [j for j in body_set if PERF_INCLUDES_RE.search(lines[j])]
        if includes_hits:
            perf.append(_finding(
                "performance", "MEDIUM", path, _enclosing_symbol(symbols, li + 1), includes_hits[0] + 1,
                "Linear membership search inside a loop (possible O(n²))",
                _snippet(lines, includes_hits[0]),
                "Array.includes/indexOf/find scan the whole array on every iteration, compounding with the outer loop (static detection).",
                "Build a Set/Map of lookup values before the loop for constant-time access.",
            ))
        if any(PERF_NEWREGEX_RE.search(lines[j]) for j in body_set):
            perf.append(_finding(
                "performance", "LOW", path, _enclosing_symbol(symbols, li + 1), li + 1,
                "RegExp constructed inside a loop",
                _snippet(lines, li),
                "Compiling a regular expression repeatedly wastes CPU on every iteration.",
                "Hoist the RegExp construction outside the loop."))

    for i, l in enumerate(lines):
        if PERF_DEEP_CLONE_RE.search(l):
            add("performance", "LOW", i, "Deep clone via JSON.parse(JSON.stringify(...))",
                "Serializing then parsing is slow for large objects and drops functions, Dates, Maps and Sets.",
                "Use structuredClone() or a targeted shallow copy.")
            break

    if lang in ("TypeScript", "JavaScript"):
        sync_hits = [i for i, l in enumerate(lines) if PERF_SYNCIO_RE.search(l)]
        if sync_hits:
            add("performance", "MEDIUM", sync_hits[0], "Synchronous filesystem/API call",
                "*Sync calls block the event loop until they finish, stalling every concurrent request (static detection).",
                "Use the async equivalents (fs/promises) so the event loop stays free.")
    elif lang == "Python":
        req_hits = [i for i, l in enumerate(lines) if PY_PERF_REQUESTS_RE.search(l)]
        if req_hits:
            add("performance", "MEDIUM", req_hits[0], "Blocking HTTP client (requests)",
                "The requests library blocks the thread during network I/O; inside async servers this stalls the whole event loop.",
                "Switch to httpx.AsyncClient or aiohttp for non-blocking requests.")
        sleep_hits = [i for i, l in enumerate(lines) if PY_SLEEP_RE.search(l)]
        if sleep_hits:
            add("performance", "LOW", sleep_hits[0], "Busy-wait sleep detected",
                "time.sleep blocks the executing thread entirely.",
                "Use asyncio.sleep in async contexts or event-based waiting.")

    # repeated identical awaited calls within one function
    if lang in ("TypeScript", "JavaScript"):
        for start, end, name in symbols:
            calls: Dict[str, int] = {}
            first_line = 0
            for j in range(max(0, start - 1), min(end, n)):
                mm = re.search(r"\bawait\s+([A-Za-z_$][\w$.]*)\s*\(", lines[j])
                if mm:
                    key = mm.group(1)
                    if key not in calls:
                        calls[key] = 0
                        first_line = j
                    calls[key] += 1
            for key, cnt in calls.items():
                if cnt >= 4:
                    perf.append(_finding(
                        "performance", "MEDIUM", path, name, first_line + 1,
                        f"Awaited '{key}()' called {cnt}x in one function",
                        _snippet(lines, first_line),
                        "Repeated identical async calls multiply latency and load on the downstream service (static count).",
                        "Cache the result, hoist it out, or batch the requests.",
                    ))

    # large function check
    for start, end, name in symbols:
        length = end - start + 1
        if length > 120:
            issues.append(_finding(
                "health", "MEDIUM", path, name, start,
                f"Very long {('function' if '(' in name else 'class')} ({length} lines)",
                f"{name}: lines {start}-{end}",
                "Functions beyond ~100 lines are hard to test, review and modify safely; change risk rises sharply with size.",
                "Split into smaller focused helpers with clear responsibilities.",
            ))


def _explain_health(problem: str) -> Tuple[str, str]:
    table = {
        "Use of eval()": ("Evaluating dynamic strings as code allows attackers to inject payloads and prevents JIT optimization.", "Eliminate eval; use JSON.parse or explicit parsing."),
        "Empty catch block swallows errors": ("Failures disappear without trace, corrupting state silently and prolonging outages.", "Log and wrap or rethrow the error."),
        "Empty catch block": ("Errors are discarded without handling.", "Add logging or propagate."),
        "Debugger statement left in code": ("Halts execution when devtools are open.", "Remove it."),
        "Assignment to innerHTML": ("Unsanitized HTML enables XSS.", "Use textContent or DOMPurify."),
        "Explicit 'any' type": ("Disables compile-time safety for that value.", "Introduce precise types."),
        "Bare except swallows errors": ("Catches everything including system exits, masking bugs.", "Catch specific exceptions."),
        "Exception silenced without handling": ("Hides real failures from logs and monitors.", "Log or re-raise."),
        "Use of exec()": ("Arbitrary code execution vector.", "Avoid dynamic execution."),
        "Pickle deserialization": ("Untrusted pickles can execute code on load.", "Use JSON for untrusted data."),
        "Assert used for validation": ("Removed under optimization flags.", "Raise explicit errors."),
        "Unresolved TODO/FIXME marker": ("Tracks known incomplete or risky work.", "Resolve or convert to a tracked issue."),
        "Console debug statement": ("Noisy output leaks internals to browser consoles.", "Remove or route through a logger."),
        "Print statement instead of logger": ("Unstructured output bypasses log levels and aggregation.", "Use the standard logging module."),
    }
    return table.get(problem, ("This pattern increases defect risk or maintenance cost.", "Follow language best practices to remediate."))


# ── Health scoring ────────────────────────────────────────────────

def _clamp(v: float) -> int:
    return int(max(0, min(100, round(v))))


def compute_scores(stats: Dict[str, Any], issues: List[Dict[str, Any]], perf: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_sev = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    sec_count = 0
    for iss in issues:
        by_sev[iss["severity"]] = by_sev.get(iss["severity"], 0) + 1
        if iss["category"] == "security":
            sec_count += 1
    high_perf = sum(1 for p in perf if p["severity"] in ("CRITICAL", "HIGH"))

    analyzed = max(1, stats["analyzed_files"])
    kaf = 1000.0 * analyzed / max(50, stats["lines_of_code"]) ** 0.25  # normalize by codebase size

    reliability = 100 - 8 * by_sev["CRITICAL"] - 4 * by_sev["HIGH"] - 1.5 * by_sev["MEDIUM"]
    maintainability = 100 - 2.5 * (stats["long_files"] + stats["long_functions"]) / analyzed * 220 - 0.6 * by_sev["LOW"] / analyzed * 60
    quality = 100 - (by_sev["LOW"] / analyzed) * 260 - 2 * by_sev["MEDIUM"] / analyzed * 40
    security = 100 - 18 * sec_count - 3 * by_sev["CRITICAL"]

    src = max(1, stats["source_files"])
    ratio = stats["test_files"] / src
    coverage = _clamp(20 + 160 * min(ratio, 0.5))
    avg_cc = stats.get("avg_complexity", 1.0)
    complexity = _clamp(108 - 16 * avg_cc)
    dep_health = _clamp(88 - 0.35 * stats["external_dependencies"] ** 0.85 + (8 if stats["has_lockfile"] else 0))

    overall_components = [
        reliability * 0.22, maintainability * 0.18, quality * 0.14,
        security * 0.16, coverage * 0.10, complexity * 0.12, dep_health * 0.08,
    ]
    overall = _clamp(sum(overall_components) - high_perf * 0.5)

    return {
        "overall": overall,
        "categories": {
            "Reliability": _clamp(reliability),
            "Maintainability": _clamp(maintainability),
            "Code Quality": _clamp(quality),
            "Security": _clamp(security),
            "Test Coverage": coverage,
            "Complexity": complexity,
            "Dependency Health": dep_health,
        },
        "counts": {
            "critical": by_sev["CRITICAL"], "high": by_sev["HIGH"],
            "medium": by_sev["MEDIUM"], "low": by_sev["LOW"],
            "security_findings": sec_count,
            "performance_findings": len(perf),
        },
        "methodology": "Deterministic weighted scoring over static-analysis findings normalized by codebase size. Not a runtime audit.",
    }


# ── Recommendations ───────────────────────────────────────────────

_PRIORITY_MAP = {"CRITICAL": "P1", "HIGH": "P1", "MEDIUM": "P2", "LOW": "P3"}
_BENEFIT_MAP = {
    "CRITICAL": "Removes a severe defect/security exposure",
    "HIGH": "Materially reduces failure risk and debugging time",
    "MEDIUM": "Improves robustness and readability",
    "LOW": "Polishes code hygiene",
}


def build_recommendations(issues: List[Dict[str, Any]], perf: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    pool = issues + perf
    pool.sort(key=lambda x: SEV_ORDER.get(x["severity"], 99))
    seen_files: Dict[str, int] = {}
    recs: List[Dict[str, Any]] = []
    for f in pool:
        if seen_files.get(f["file"], 0) >= 2:
            continue
        seen_files[f["file"]] = seen_files.get(f["file"], 0) + 1
        if len(recs) >= 25:
            break
        recs.append({
            "id": f["id"],
            "file": f["file"],
            "symbol": f["symbol"] or "—",
            "current_problem": f["problem"],
            "why_it_matters": f["explanation"],
            "recommended_solution": f["recommendation"],
            "priority": _PRIORITY_MAP.get(f["severity"], "P3"),
            "expected_benefit": _BENEFIT_MAP.get(f["severity"], "Improves overall quality"),
            "category": f["category"],
            "severity": f["severity"],
            "source": "static-analysis",
        })
    return recs


# ── Report cache / history ────────────────────────────────────────

def _cache_path(rid: str) -> str:
    return os.path.join(_INTEL_DIR, f"{rid}.json")


def save_report(rid: str, report: Dict[str, Any]) -> None:
    try:
        os.makedirs(_INTEL_DIR, exist_ok=True)
        history: List[Dict[str, Any]] = []
        prev = load_report(rid)
        if prev:
            history = prev.get("history", [])
        history = history[-19:] + [{
            "ts": report["generated_at"],
            "overall": report["health"]["overall"],
        }]
        report["history"] = history
        with open(_cache_path(rid), "w") as fh:
            json.dump(report, fh)
    except Exception:
        pass


def load_report(rid: str) -> Optional[Dict[str, Any]]:
    try:
        with open(_cache_path(rid)) as fh:
            return json.load(fh)
    except Exception:
        return None


# ── Main scan pipeline ────────────────────────────────────────────

async def _fetch_all(token: str, owner: str, repo: str, ref: str,
                     paths: List[Dict[str, Any]]) -> Dict[str, str]:
    sem = asyncio.Semaphore(12)
    contents: Dict[str, str] = {}

    async def fetch(item: Dict[str, Any]) -> None:
        async with sem:
            try:
                text = await get_file_content(token, owner, repo, item["path"], ref)
                if text is not None:
                    contents[item["path"]] = text
            except Exception:
                pass

    await asyncio.gather(*(fetch(p) for p in paths))
    return contents


async def run_intelligence_scan(job_id: str, token: str, pipelines_fn: Callable[..., Any]) -> None:
    job = _intel_jobs.get(job_id)
    if not job:
        return
    rid = repo_id(job.owner, job.repo)
    started = int(time.time())

    try:
        # Stage 0 — Scanning Repository
        _set_stage(job, 0, 0.05)
        tree = await get_file_tree(token, job.owner, job.repo, job.branch)
        blobs = [t for t in tree if t.get("type") == "blob"]
        if not blobs:
            raise RuntimeError("Repository is empty or inaccessible")

        filtered = filter_files(tree)
        code_items = [f for f in filtered if detect_language(f["path"]) in CODE_LANGS]
        code_items.sort(key=lambda f: -(f.get("size") or 0))
        code_items = [f for f in code_items if (f.get("size") or 0) <= MAX_ANALYSIS_BYTES][:MAX_CONTENT_FILES]

        # Stage 1 — Analyzing Files
        _set_stage(job, 1, 0.15)
        contents = await _fetch_all(token, job.owner, job.repo, job.branch, code_items)

        # Stages 2-4 — entities, deps, per-file rules
        languages: Dict[str, Dict[str, int]] = {}
        total_classes = total_functions = total_methods = 0
        external_deps: Dict[str, int] = {}
        internal_imports = 0
        test_files = source_files = 0
        lines_of_code = 0
        long_files = long_functions = 0
        complexities: List[float] = []
        symbols_by_file: Dict[str, List[Tuple[int, int, str]]] = {}
        imports_by_file: Dict[str, List[str]] = {}
        issues: List[Dict[str, Any]] = []
        perf: List[Dict[str, Any]] = []

        total = max(1, len(code_items))
        for idx, item in enumerate(code_items):
            path, size = item["path"], item.get("size", 0)
            lang = detect_language(path)
            content = contents.get(path)
            if content is None:
                continue

            loc = content.count("\n") + 1
            lines_of_code += loc
            entry = languages.setdefault(lang, {"files": 0, "lines": 0})
            entry["files"] += 1
            entry["lines"] += loc

            is_test = bool(TEST_FILE_RE.search(path))
            if is_test:
                test_files += 1
            else:
                source_files += 1
            if loc > 600:
                long_files += 1
                issues.append(_finding(
                    "health", "LOW", path, "", 1,
                    f"Large file ({loc} lines)",
                    f"{path}: {loc} lines",
                    "Very large files concentrate many responsibilities and produce wide-blast-radius changes.",
                    "Split along cohesive boundaries (feature, layer, or domain).",
                ))

            syms: List[Tuple[int, int, str]] = []
            imports: List[str] = []
            if lang in ("TypeScript", "JavaScript"):
                fa = analyze_file(content, path)
                if fa:
                    d = fa.to_dict()
                    for fn in d["functions"]:
                        total_functions += 1
                        syms.append((fn["start_line"], fn["end_line"], f"{fn['name']}()"))
                    for cl in d["classes"]:
                        total_classes += 1
                        span = cl["end_line"] - cl["start_line"] + 1
                        if span > 250:
                            long_functions += 1
                            issues.append(_finding(
                                "health", "MEDIUM", path, cl["name"], cl["start_line"],
                                f"Very large class ({span} lines)",
                                f"class {cl['name']}: lines {cl['start_line']}-{cl['end_line']}",
                                "Classes spanning hundreds of lines usually violate single-responsibility and are risky to modify.",
                                "Extract related methods/state into collaborating classes or modules.",
                            ))
                        syms.append((cl["start_line"], cl["end_line"], f"class {cl['name']}"))
                    for me in d["methods"]:
                        total_methods += 1
                        syms.append((me["start_line"], me["end_line"], f"{me['class_name']}.{me['name']}()"))
                    imports = [im["source"] for im in d["imports"]]
                    cc_base = content
                else:
                    cc_base = content
            elif lang == "Python":
                parsed_py = _parse_python(content, path)
                for fn in parsed_py["functions"]:
                    total_functions += 1
                    syms.append((fn["start_line"], fn["end_line"], f"{fn['name']}()"))
                for cl in parsed_py["classes"]:
                    total_classes += 1
                    syms.append((cl["start_line"], cl["end_line"], f"class {cl['name']}"))
                    span = cl["end_line"] - cl["start_line"] + 1
                    if span > 250:
                        long_functions += 1
                imports = parsed_py["imports"]
                cc_base = content
            else:
                cc_base = content

            symbols_by_file[path] = syms

            # cyclomatic approximation over whole file (proxy metric)
            cc = len(re.findall(r"\b(if|elif|else if|for|while|case|catch|except|and\b|\|\||&&|\?\?)\b", cc_base))
            complexities.append(1 + cc / max(1, len(syms) or 1))

            # dependency classification
            for imp in imports:
                root = imp.lstrip("@").split("/")[0]
                if imp.startswith(".") or imp.startswith("/") or imp.startswith("@/") or imp.startswith("~/"):
                    internal_imports += 1
                elif root in ("react", "react-dom", "next", "vue", "angular", "express", "fastapi", "httpx", "numpy", "pandas"):
                    external_deps[root] = external_deps.get(root, 0) + 1
                else:
                    external_deps[root] = external_deps.get(root, 0) + 1

            _scan_content_rules(path, lang, content, syms, issues, perf)

            if (idx + 1) % 20 == 0:
                stage = 1 if idx < total * 0.5 else 2
                _set_stage(job, stage, 0.15 + 0.45 * ((idx + 1) / total))
                job.message = f"{SCAN_STAGES[stage]}... {idx + 1}/{total}"

        # Stage 4 — Analyzing Dependencies (manifest-level)
        _set_stage(job, 4, 0.62)
        has_lockfile = any(b["path"].endswith(("package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock", "Pipfile.lock", "Cargo.lock")) for b in blobs)
        manifest_paths = [b["path"] for b in blobs if b["path"].endswith(("package.json", "requirements.txt", "pyproject.toml"))]
        manifest_contents = await _fetch_all(token, job.owner, job.repo, job.branch, [{"path": p} for p in manifest_paths[:5]])
        manifest_deps = 0
        for mp, mc in manifest_contents.items():
            try:
                if mp.endswith("package.json"):
                    data = json.loads(mc)
                    manifest_deps += len(data.get("dependencies", {}) or {}) + len(data.get("devDependencies", {}) or {})
                elif mp.endswith("requirements.txt"):
                    manifest_deps += len([l for l in mc.splitlines() if l.strip() and not l.startswith("#")])
                elif mp.endswith("pyproject.toml"):
                    manifest_deps += len(re.findall(r"^\s*\"?[A-Za-z0-9_.\-]+\s*=", mc, re.MULTILINE))
            except Exception:
                continue

        # contributors/commits (best effort)
        contributors = await get_contributors_count(token, job.owner, job.repo)
        commits = await get_commits_count(token, job.owner, job.repo)

        # Stage 5 — Checking Pipelines
        _set_stage(job, 5, 0.72)
        pipelines = await pipelines_fn(token, job.owner, job.repo, tree)

        # Stage 6 — Checking Performance (rules already ran; finalize counts)
        _set_stage(job, 6, 0.82)
        stats = {
            "total_files": len(blobs),
            "filtered_files": len(filtered),
            "analyzed_files": len(contents),
            "source_files": source_files,
            "test_files": test_files,
            "lines_of_code": lines_of_code,
            "languages": languages,
            "language_count": len(languages),
            "classes": total_classes,
            "functions": total_functions,
            "methods": total_methods,
            "external_dependencies": manifest_deps or sum(external_deps.values()),
            "unique_external_imports": sorted(external_deps.keys())[:200],
            "internal_imports": internal_imports,
            "contributors": contributors,
            "commits": commits,
            "has_lockfile": has_lockfile,
            "long_files": long_files,
            "long_functions": long_functions,
            "avg_complexity": round(sum(complexities) / len(complexities), 2) if complexities else 1.0,
        }

        # Stage 7 — Calculating Code Health
        _set_stage(job, 7, 0.92)
        health = compute_scores(stats, issues, perf)
        recommendations = build_recommendations(issues, perf)

        report = {
            "owner": job.owner,
            "repo": job.repo,
            "branch": job.branch,
            "generated_at": started,
            "stats": stats,
            "health": health,
            "issues": sorted(issues, key=lambda x: SEV_ORDER.get(x["severity"], 99))[:300],
            "performance_issues": sorted(perf, key=lambda x: SEV_ORDER.get(x["severity"], 99))[:200],
            "recommendations": recommendations,
            "pipelines": pipelines,
        }
        save_report(rid, report)

        job.status = "completed"
        job.progress = 1.0
        job.stage = len(SCAN_STAGES) - 1
        job.message = "Code intelligence scan complete"
    except Exception as exc:
        job.status = "failed"
        job.error = str(exc)
        job.message = f"Scan failed: {exc}"
