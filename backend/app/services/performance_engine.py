"""Static performance analysis engine.

Every finding produced here is a STATIC pattern detection. The engine never
claims measured timing — titles/messages always frame results as
"Potential Performance Issue" and the report carries an explicit
``analysis_kind`` field so the UI can label findings

    STATIC ANALYSIS  (this engine)
    MEASURED PERFORMANCE (not available unless a profiler is integrated)

Confidence mirrors the security engine:
  HIGH   deterministic pattern with direct performance semantics
  MEDIUM strong indication, impact depends on data sizes/usage
  LOW    heuristic / potential issue
"""

from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, List, Tuple

STATIC_LABEL = "Potential Performance Issue (static analysis)"

# loop openers for common syntaxes
LOOP_RE = re.compile(
    r"^\s*(for\s*\(|while\s*\(|for\s+\w+\s+in\s|foreach|\.(forEach|map)\(|do\s*\{)"
)
AWAIT_RE = re.compile(r"\bawait\s+")
MEMBERSHIP_RE = re.compile(r"\.(includes|indexOf|find|findIndex|some|every)\s*\(")
DEEP_CLONE_RE = re.compile(r"JSON\.parse\s*\(\s*JSON\.stringify")
NEW_REGEX_RE = re.compile(r"new\s+RegExp\s*\(")
SYNC_IO_RE = re.compile(r"\b(readFileSync|writeFileSync|existsSync|readdirSync|execSync|statSync)\b")
PY_BLOCKING_RE = re.compile(r"\brequests\.(get|post|put|delete|head|patch)\s*\(")
PY_SLEEP_RE = re.compile(r"\btime\.sleep\s*\(")
STRING_CONCAT_LOOP_RE = re.compile(r"\w+\s*\+=\s*['\"`]")
INDEX_WRITE_RE = re.compile(r"\b(arr|list|items|results)\[\w+\]\s*=")

SEV_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}


def _fingerprint(path: str, rule_id: str, line: int) -> str:
    return hashlib.sha1(f"{path}:{rule_id}:{line}".encode()).hexdigest()[:16]


def _finding(path: str, rule_id: str, severity: str, confidence: str,
             line: int, symbol: str, title: str, snippet: str, why: str,
             recommendation: str) -> Dict[str, Any]:
    return {
        "rule_id": rule_id,
        "title": f"{STATIC_LABEL}: {title}" if not title.startswith(STATIC_LABEL) else title,
        "severity": severity,
        "confidence": confidence,
        "file": path,
        "line": line,
        "symbol": symbol,
        "evidence": snippet[:400],
        "why": why,
        "recommendation": recommendation,
        "standards": [],  # performance has no security standard mapping by design
        "detection_method": "Regex/indentation heuristic over source",
        "source": "static-analysis",
        "category_label": "performance",
        "fingerprint": _fingerprint(path, rule_id, line),
        "measured": False,
        "note": "Static detection only — no runtime measurement was performed.",
    }


def _loop_body(lines: List[str], start: int) -> Tuple[int, List[int]]:
    """Return (indent, body_line_indices) of the loop starting at `start`."""
    indent = len(lines[start]) - len(lines[start].lstrip())
    body: List[int] = []
    n = len(lines)
    for j in range(start + 1, min(start + 120, n)):
        stripped = lines[j].strip()
        if not stripped or stripped.startswith(("//", "#", "*", "/*")):
            continue
        j_indent = len(lines[j]) - len(lines[j].lstrip())
        if j_indent <= indent:
            break
        body.append(j)
    return indent, body


def scan_file_performance(
    path: str, lang: str, content: str,
    symbols: List[Tuple[int, int, str]],
) -> List[Dict[str, Any]]:
    lines = content.splitlines()
    n = len(lines)
    out: List[Dict[str, Any]] = []

    def sym_at(line_0: int) -> str:
        for start, end, name in symbols:
            if start <= line_0 + 1 <= end:
                return name
        return ""

    # ── nested loops → O(n²) or worse ────────────────────────────────
    reported_nested: set = set()
    for i in range(n):
        if not LOOP_RE.match(lines[i]):
            continue
        indent_i, body_i = _loop_body(lines, i)
        for j in body_i:
            if LOOP_RE.match(lines[j]):
                key = sym_at(i) or i
                if key in reported_nested:
                    break
                reported_nested.add(key)
                out.append(_finding(
                    path, "PERF-NESTED-LOOPS", "HIGH", "MEDIUM", i + 1, sym_at(i),
                    "Nested loops detected",
                    "\n".join(lines[i:min(i + 3, n)]),
                    "Nested iteration multiplies work; as inputs grow this behaves O(n²) or worse. Impact depends on realistic input sizes.",
                    "Flatten nesting, precompute a hash map for lookups, or restructure the algorithm.",
                ))
                break

    # ── awaited calls inside loops (sequential I/O) ──────────────────
    for i in range(n):
        if not LOOP_RE.match(lines[i]):
            continue
        _, body = _loop_body(lines, i)
        await_hits = [j for j in body if AWAIT_RE.search(lines[j])]
        if await_hits:
            out.append(_finding(
                path, "PERF-AWAIT-IN-LOOP", "MEDIUM", "HIGH", await_hits[0] + 1, sym_at(i),
                "Sequential awaited call inside a loop",
                "\n".join(lines[await_hits[0]:min(await_hits[0] + 2, n)]),
                "Each await blocks the iteration until completion, so total latency grows linearly with the number of iterations.",
                "Gather promises and resolve concurrently (Promise.all / asyncio.gather), or batch requests server-side.",
            ))

    # ── linear membership search inside loops ────────────────────────
    for i in range(n):
        if not LOOP_RE.match(lines[i]):
            continue
        _, body = _loop_body(lines, i)
        hits = [j for j in body if MEMBERSHIP_RE.search(lines[j])]
        if hits:
            out.append(_finding(
                path, "PERF-LINEAR-SEARCH-IN-LOOP", "MEDIUM", "MEDIUM", hits[0] + 1, sym_at(i),
                "Linear membership search inside a loop",
                "\n".join(lines[hits[0]:min(hits[0] + 2, n)]),
                "includes/indexOf/find scan the entire collection per iteration, compounding with the outer loop into possible O(n²).",
                "Build a Set/Map of lookup keys once before the loop.",
            ))

    # ── regex construction inside loops ──────────────────────────────
    for i in range(n):
        if not LOOP_RE.match(lines[i]):
            continue
        _, body = _loop_body(lines, i)
        hits = [j for j in body if NEW_REGEX_RE.search(lines[j])]
        if hits:
            out.append(_finding(
                path, "PERF-REGEX-IN-LOOP", "LOW", "HIGH", hits[0] + 1, sym_at(i),
                "RegExp constructed inside a loop",
                "\n".join(lines[hits[0]:min(hits[0] + 2, n)]),
                "Recompiling the same regular expression each iteration wastes CPU.",
                "Hoist RegExp creation outside the loop.",
            ))

    # ── string building via += inside loops ──────────────────────────
    for i in range(n):
        if not LOOP_RE.match(lines[i]):
            continue
        _, body = _loop_body(lines, i)
        hits = [j for j in body if STRING_CONCAT_LOOP_RE.search(lines[j])]
        if hits:
            out.append(_finding(
                path, "PERF-STRCAT-IN-LOOP", "LOW", "LOW", hits[0] + 1, sym_at(i),
                "String concatenation with += inside a loop",
                "\n".join(lines[hits[0]:min(hits[0] + 2, n)]),
                "Repeated string concatenation can allocate a new string per iteration on some engines; large loops become quadratic in memory copies.",
                "Collect parts in an array and join() once, or use a StringBuilder equivalent.",
            ))

    # ── deep clone anti-pattern ──────────────────────────────────────
    for i, l in enumerate(lines):
        if DEEP_CLONE_RE.search(l):
            out.append(_finding(
                path, "PERF-JSON-CLONE", "LOW", "HIGH", i + 1, sym_at(i),
                "Deep clone via JSON.parse(JSON.stringify(...))",
                l.strip(),
                "Serialize+parse round-trip is CPU-heavy for large objects and silently drops functions, Dates, Maps and Sets.",
                "Use structuredClone() or a purpose-built clone.",
            ))
            break

    # ── blocking I/O ─────────────────────────────────────────────────
    if lang in ("JavaScript", "TypeScript"):
        hits = [i for i, l in enumerate(lines) if SYNC_IO_RE.search(l)]
        if hits:
            out.append(_finding(
                path, "PERF-SYNC-IO", "MEDIUM", "HIGH", hits[0] + 1, sym_at(hits[0]),
                "Synchronous filesystem call",
                lines[hits[0]].strip(),
                "*Sync variants block the event loop until they finish, stalling every concurrent request.",
                "Use fs/promises equivalents.",
            ))
    elif lang == "Python":
        hits = [i for i, l in enumerate(lines) if PY_BLOCKING_RE.search(l)]
        if hits:
            out.append(_finding(
                path, "PERF-BLOCKING-HTTP", "MEDIUM", "HIGH", hits[0] + 1, sym_at(hits[0]),
                "Blocking HTTP client (requests)",
                lines[hits[0]].strip(),
                "The requests library occupies the thread for the whole round-trip; inside async servers it stalls the event loop.",
                "Use httpx.AsyncClient or aiohttp.",
            ))
        hits = [i for i, l in enumerate(lines) if PY_SLEEP_RE.search(l)]
        if hits:
            out.append(_finding(
                path, "PERF-BUSY-WAIT", "LOW", "HIGH", hits[0] + 1, sym_at(hits[0]),
                "Blocking sleep call",
                lines[hits[0]].strip(),
                "time.sleep parks the whole thread; in async contexts it blocks the loop.",
                "Use asyncio.sleep in async code.",
            ))

    # ── very large functions (maintainability + perf review cost) ────
    for start, end, name in symbols:
        length = end - start + 1
        if length > 150 and "(" in name and not name.startswith("class"):
            out.append(_finding(
                path, "PERF-LARGE-FUNCTION", "LOW", "HIGH", start, name,
                f"Large function ({length} lines)",
                f"{name}: lines {start}-{end}",
                "Very large functions are slow to JIT-optimize, hard to test, and often contain hidden repeated work worth extracting.",
                "Split into focused helpers; profile before micro-optimizing.",
            ))

    out.sort(key=lambda f: SEV_ORDER.get(f["severity"], 99))
    return out
