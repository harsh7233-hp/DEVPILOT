"""Code metrics extraction + transparent health scoring.

All values are MEASURED from repository content during the deep scan:
cyclomatic complexity (AST for Python, keyword approximation for JS/TS),
function/file sizes, duplication ratio, documentation coverage, test-file
share, dependency counts and reliability-relevant patterns.

SCORING MODEL — every factor uses a fixed, published formula. No AI
involvement. Each factor returns its score, weight, the raw measurements and
the exact formula string so the UI can answer "How is this calculated?".
Factors that cannot be measured are marked unavailable and their weight is
redistributed across available factors (documented behaviour).
"""

from __future__ import annotations

import ast
import hashlib
import re
from typing import Any, Dict, List, Optional, Tuple

# ── Public constants shown in the UI ─────────────────────────────────

FACTOR_WEIGHTS = {
    "complexity": 0.18,
    "maintainability": 0.16,
    "duplication": 0.12,
    "tests": 0.18,
    "documentation": 0.08,
    "dependencies": 0.10,
    "reliability": 0.18,
}

FORMULAS = {
    "code_health": (
        "Code Health = Σ(factor score × weight) over available factors "
        "(weights renormalized when a factor is unavailable). Weights: "
        + ", ".join(f"{k} {v:.2f}" for k, v in FACTOR_WEIGHTS.items())
    ),
    "complexity": "100 × (1 − max(0, avg_cyclomatic_complexity − 5) / 20)",
    "maintainability": "0.6 × function_size_score + 0.4 × file_size_score; "
                       "function_size = 100 × (1 − min(1, avg_function_lines/80)); "
                       "file_size = 100 × (1 − min(1, median_file_lines/400))",
    "duplication": "100 × (1 − min(1, duplicated_line_ratio / 0.15)); duplicated lines = "
                   "lines inside repeated normalized 6-line windows ÷ total code lines",
    "tests": "min(100, round(test_file_share / 0.30 × 100)) where share = test files ÷ "
             "(test + source files). Static file-share proxy — NOT runtime coverage.",
    "documentation": "100 × documented_symbols ÷ symbols (Python docstrings; JSDoc block "
                     "immediately above functions/classes for JS/TS)",
    "dependencies": "clamp(60 + 15×lockfile − min(40, 0.4 × direct_dependency_count)); "
                    "unavailable when no manifest exists",
    "reliability": "100 − min(70, 8×critical + 3×high + 1×medium) where counts are "
                   "error-handling findings per severity from static analysis",
    "performance_card": "100 − min(100, performance_findings_per_KLOC × 40); "
                        "STATIC ANALYSIS ONLY — no measured timing",
    "security_posture": "posture = max(0, round(base − deduction)); "
                        "base = 100 × passed_checks ÷ executed_checks; "
                        "deduction = min(60, Σ open_findings × points[severity] × confidence_factor); "
                        "points: CRITICAL 20, HIGH 12, MEDIUM 6, LOW 2; "
                        "confidence factors: HIGH 1.0, MEDIUM 0.6, LOW 0.25",
}


def clamp(v: float) -> int:
    return int(max(0, min(100, round(v))))


# ── Function extraction & complexity ────────────────────────────────

class FuncInfo:
    __slots__ = ("name", "start", "end", "cc", "params", "doc", "max_nesting")

    def __init__(self, name: str, start: int, end: int, cc: int,
                 params: int, doc: bool, max_nesting: int) -> None:
        self.name = name
        self.start = start
        self.end = end
        self.cc = cc
        self.params = params
        self.doc = doc
        self.max_nesting = max_nesting


def _py_functions(content: str) -> Tuple[List[FuncInfo], int]:
    """Accurate AST-based extraction for Python. Returns (functions, classes_count)."""
    funcs: List[FuncInfo] = []
    classes = 0
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return funcs, 0

    def cc_of(node: ast.AST) -> Tuple[int, int]:
        """Cyclomatic complexity = 1 + decision points; also max nesting depth."""
        cc = 1
        max_depth = 0
        match_node = getattr(ast, "Match", None)

        def walk(n: ast.AST, depth: int) -> None:
            nonlocal cc, max_depth
            for child in ast.iter_child_nodes(n):
                if isinstance(child, (ast.If, ast.For, ast.While, ast.AsyncFor,
                                      ast.ExceptHandler, ast.With, ast.AsyncWith,
                                      ast.Assert, ast.IfExp)):
                    cc += 1
                    walk(child, depth + 1)
                elif isinstance(child, ast.BoolOp):
                    cc += len(child.values) - 1
                    walk(child, depth)
                elif isinstance(child, ast.comprehension):
                    cc += 1 + len(child.ifs)
                    walk(child, depth + 1)
                elif match_node is not None and isinstance(child, match_node):
                    cc += len(child.cases)
                    walk(child, depth + 1)
                elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # nested defs counted separately by outer iteration
                    walk(child, depth)
                else:
                    walk(child, depth)
                max_depth = max(max_depth, depth)

        walk(node, 0)
        return cc, max_depth

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            cc, nesting = cc_of(node)
            end = getattr(node, "end_lineno", node.lineno) or node.lineno
            has_doc = bool(ast.get_docstring(node))
            funcs.append(FuncInfo(
                name=node.name, start=node.lineno, end=end, cc=cc,
                params=len(node.args.args) + len(node.args.kwonlyargs),
                doc=has_doc, max_nesting=nesting,
            ))
        elif isinstance(node, ast.ClassDef):
            classes += 1
    return funcs, classes


_JS_DECISION_RE = re.compile(
    r"\b(if|for|while|case|catch)\b|\?[^?.]|&&|\|\||\?\?"
)


def _js_functions(content: str) -> List[FuncInfo]:
    """Approximate extraction via regex boundaries (tree-sitter not required).

    Counts decisions inside each function body by brace tracking. Documented as
    an APPROXIMATION in the UI.
    """
    funcs: List[FuncInfo] = []
    pattern = re.compile(
        r"(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)|"
        r"(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>",
    )
    matches = list(pattern.finditer(content))
    for i, m in enumerate(matches):
        name = m.group(1) or m.group(3) or ""
        start_off = m.start()
        # find opening brace after match, then track to matching close
        brace_idx = content.find("{", m.end() - 1)
        if brace_idx == -1:
            arrow_end = content.find("\n", m.end())
            brace_idx = content.find("{", m.end(), arrow_end if arrow_end != -1 else len(content))
        if brace_idx == -1:
            continue
        depth = 0
        end_off = brace_idx
        for k in range(brace_idx, len(content)):
            ch = content[k]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end_off = k
                    break
        body = content[brace_idx:end_off]
        line_start = content.count("\n", 0, brace_idx) + 1
        line_end = content.count("\n", 0, end_off) + 1
        cc = 1 + len(_JS_DECISION_RE.findall(body))
        params = len((m.group(2) or "").split(",")) if m.group(2) else 0
        # JSDoc directly above?
        pre_start = content.rfind("\n\n", 0, start_off)
        prefix = content[max(pre_start, start_off - 400):start_off]
        doc = bool(re.search(r"/\*\*[\s\S]*\*/\s*$", prefix))
        funcs.append(FuncInfo(name=name, start=line_start, end=line_end,
                              cc=min(cc, 200), params=params, doc=doc, max_nesting=0))
    return funcs


def extract_functions(path: str, lang: str, content: str) -> Tuple[List[FuncInfo], Optional[str]]:
    """Returns (functions, parser_used) — parser_used documents the method."""
    if lang == "Python":
        fns, _ = _py_functions(content)
        return fns, "python-ast (accurate cyclomatic complexity)"
    if lang in ("JavaScript", "TypeScript"):
        return _js_functions(content), "brace-tracking approximation for JS/TS (decision keywords)"
    return [], None


# ── Duplication detection ────────────────────────────────────────────

_WINDOW = 6
_MIN_TOKENS = 30


def _normalize_line(line: str) -> str:
    return re.sub(r"\s+", " ", line.strip())


def duplication_ratio(files: Dict[str, str]) -> Dict[str, Any]:
    """Exact-match duplicate-block detection.

    A line belongs to a duplicate block when its normalized form appears in an
    identical 6-line sliding window in more than one location across the
    analyzed set. Trivial short lines are ignored.
    """
    window_counts: Dict[str, int] = {}
    windows_by_pos: Dict[Tuple[str, int], str] = {}

    for path, content in files.items():
        norm = [_normalize_line(l) for l in content.splitlines()]
        for i in range(len(norm) - _WINDOW + 1):
            chunk_lines = norm[i:i + _WINDOW]
            joined = "\n".join(chunk_lines)
            if len(joined.replace(" ", "")) < _MIN_TOKENS:
                continue
            key = hashlib.sha1(joined.encode()).hexdigest()
            window_counts[key] = window_counts.get(key, 0) + 1
            windows_by_pos[(path, i)] = key

    dup_lines = 0
    total_lines = 0
    locations: Dict[str, Dict[str, Any]] = {}
    for path, content in files.items():
        norm = [_normalize_line(l) for l in content.splitlines()]
        total_lines += len([l for l in norm if l])
        flagged = [False] * len(norm)
        for i in range(len(norm) - _WINDOW + 1):
            key = windows_by_pos.get((path, i))
            if key and window_counts.get(key, 0) > 1:
                for j in range(i, i + _WINDOW):
                    if norm[j]:
                        flagged[j] = True
        count = sum(1 for f in flagged if f)
        dup_lines += count
        if count >= _WINDOW * 2:
            first = next((k for k, f in enumerate(flagged) if f), 0)
            locations[path] = {"duplicated_lines": count, "first_block_line": first + 1}
    ratio = (dup_lines / total_lines) if total_lines else 0.0
    return {
        "duplicated_lines": dup_lines,
        "total_code_lines": total_lines,
        "ratio": round(ratio, 4),
        "top_locations": sorted(
            [{"file": p, **v} for p, v in locations.items()],
            key=lambda x: -x["duplicated_lines"],
        )[:5],
    }


# ── Smells ───────────────────────────────────────────────────────────

def detect_smells(funcs: List[FuncInfo], files: Dict[str, str]) -> Dict[str, Any]:
    long_functions = [f.name for f in funcs if (f.end - f.start + 1) > 80]
    many_params = [f.name for f in funcs if f.params > 6]
    deep_nesting = [f.name for f in funcs if f.max_nesting > 4]
    god_files = []
    for path, content in files.items():
        loc = len([l for l in content.splitlines() if l.strip()])
        if loc > 500:
            god_files.append({"file": path, "lines": loc})
    todo_markers = sum(
        len(re.findall(r"\b(TODO|FIXME|HACK|XXX)\b", c)) for c in files.values()
    )
    return {
        "long_functions": long_functions[:20],
        "long_function_count": len(long_functions),
        "too_many_params": many_params[:20],
        "too_many_params_count": len(many_params),
        "deeply_nested": deep_nesting[:20],
        "god_files": god_files,
        "todo_fixme_markers": todo_markers,
        "total": len(long_functions) + len(many_params) + len(deep_nesting) + len(god_files),
    }


# ── Reliability patterns ─────────────────────────────────────────────

RELIABILITY_PATTERNS = [
    ("critical", re.compile(r"\beval\s*\(|\bexec\s*\("), "dynamic code execution"),
    ("high", re.compile(r"catch\s*\([^)]*\)\s*\{\s*\}|except\s*:\s*(#.*)?$"), "swallowed errors (empty catch/bare except)"),
    ("medium", re.compile(r"except\s+\w+\s*:\s*(pass)?\s*$"), "silenced exception"),
]


def reliability_pattern_counts(files: Dict[str, str], langs: Dict[str, str]) -> Dict[str, int]:
    counts = {"critical": 0, "high": 0, "medium": 0}
    for path, content in files.items():
        lang = langs.get(path)
        for sev, rx, _label in RELIABILITY_PATTERNS:
            if sev == "critical" or lang in ("JavaScript", "TypeScript", "Python"):
                counts[sev] += len(rx.findall(content))
    return counts


# ── Factor scoring (each returns full transparency payload) ──────────

def _factor(name: str, score: Optional[int], weight: float,
            measurements: Dict[str, Any], formula: str) -> Dict[str, Any]:
    return {
        "key": name,
        "score": score,
        "weight": weight,
        "available": score is not None,
        "measurements": measurements,
        "formula": formula,
    }


def compute_code_health(
    funcs: List[FuncInfo],
    files: Dict[str, str],
    langs: Dict[str, str],
    stats: Dict[str, Any],
    reliability_counts: Dict[str, int],
    dependency_info: Dict[str, Any],
) -> Dict[str, Any]:
    avg_func_len = (
        sum(f.end - f.start + 1 for f in funcs) / len(funcs) if funcs else None
    )
    avg_cc = sum(f.cc for f in funcs) / len(funcs) if funcs else None

    file_locs = sorted(
        len([l for l in c.splitlines() if l.strip()]) for c in files.values()
    )
    median_loc = file_locs[len(file_locs) // 2] if file_locs else None

    dup = duplication_ratio(files)
    smells = detect_smells(funcs, files)

    # complexity
    complexity = None
    if avg_cc is not None:
        complexity = clamp(100 * (1 - max(0.0, avg_cc - 5) / 20))

    # maintainability
    maintainability = None
    func_size_score = file_size_score = None
    if avg_func_len is not None:
        func_size_score = clamp(100 * (1 - min(1.0, avg_func_len / 80)))
    if median_loc is not None:
        file_size_score = clamp(100 * (1 - min(1.0, median_loc / 400)))
    if func_size_score is not None and file_size_score is not None:
        maintainability = round(0.6 * func_size_score + 0.4 * file_size_score)

    # duplication
    duplication = clamp(100 * (1 - min(1.0, dup["ratio"] / 0.15))) if dup["total_code_lines"] else None

    # tests (static proxy)
    tests = None
    src_files = stats.get("source_files", 0)
    test_files = stats.get("test_files", 0)
    if (src_files + test_files) > 0:
        share = test_files / (src_files + test_files)
        tests = min(100, round(share / 0.30 * 100))

    # documentation
    docs = None
    if funcs:
        docs = clamp(100 * sum(1 for f in funcs if f.doc) / len(funcs))

    # dependencies
    dependencies = None
    if dependency_info.get("has_manifest"):
        dep_count = dependency_info.get("direct_dependencies", 0)
        dependencies = clamp(60 + (15 if dependency_info.get("has_lockfile") else 0) - min(40, 0.4 * dep_count))

    # reliability
    reliability = clamp(
        100 - min(70, 8 * reliability_counts.get("critical", 0)
                  + 3 * reliability_counts.get("high", 0)
                  + 1 * reliability_counts.get("medium", 0))
    )

    factors = [
        _factor("complexity", complexity, FACTOR_WEIGHTS["complexity"],
                {"avg_cyclomatic_complexity": round(avg_cc, 2) if avg_cc else None,
                 "parser_note": "per-function CC averaged"}, FORMULAS["complexity"]),
        _factor("maintainability", maintainability, FACTOR_WEIGHTS["maintainability"],
                {"avg_function_lines": round(avg_func_len, 1) if avg_func_len else None,
                 "median_file_lines": median_loc,
                 "func_size_score": func_size_score, "file_size_score": file_size_score},
                FORMULAS["maintainability"]),
        _factor("duplication", duplication, FACTOR_WEIGHTS["duplication"], dup,
                FORMULAS["duplication"]),
        _factor("tests", tests, FACTOR_WEIGHTS["tests"],
                {"test_files": test_files, "source_files": src_files,
                 "note": "static proxy — runtime coverage not measured"}, FORMULAS["tests"]),
        _factor("documentation", docs, FACTOR_WEIGHTS["documentation"],
                {"symbols": len(funcs),
                 "documented": sum(1 for f in funcs if f.doc)}, FORMULAS["documentation"]),
        _factor("dependencies", dependencies, FACTOR_WEIGHTS["dependencies"],
                dependency_info, FORMULAS["dependencies"]),
        _factor("reliability", reliability, FACTOR_WEIGHTS["reliability"],
                reliability_counts, FORMULAS["reliability"]),
    ]

    available = [f for f in factors if f["available"]]
    total_weight = sum(f["weight"] for f in available) or 1.0
    overall = round(sum(f["score"] * f["weight"] for f in available) / total_weight) if available else None

    return {
        "overall": overall,
        "factors": factors,
        "smells": smells,
        "formulas": FORMULAS,
        "methodology": (
            "Deterministic static measurement of the analyzed snapshot. Scores use "
            "fixed formulas (shown per factor); no AI involvement. Unavailable "
            "factors are excluded with weight redistribution."
        ),
    }
