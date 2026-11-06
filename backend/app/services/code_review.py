from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from app.services.ai import _call_llm, _get_api_config


# ── Data types ────────────────────────────────────────────────────

SEVERITY_CRITICAL = "CRITICAL"
SEVERITY_HIGH = "HIGH"
SEVERITY_MEDIUM = "MEDIUM"
SEVERITY_LOW = "LOW"

SEVERITY_ORDER = {
    SEVERITY_CRITICAL: 0,
    SEVERITY_HIGH: 1,
    SEVERITY_MEDIUM: 2,
    SEVERITY_LOW: 3,
}


class ReviewIssue:
    __slots__ = ("severity", "title", "explanation", "file", "line", "suggestion", "source")

    def __init__(
        self,
        severity: str,
        title: str,
        explanation: str,
        file: str = "",
        line: Optional[int] = None,
        suggestion: str = "",
        source: str = "static",
    ) -> None:
        self.severity = severity
        self.title = title
        self.explanation = explanation
        self.file = file
        self.line = line
        self.suggestion = suggestion
        self.source = source

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "severity": self.severity,
            "title": self.title,
            "explanation": self.explanation,
            "source": self.source,
        }
        if self.file:
            d["file"] = self.file
        if self.line is not None:
            d["line"] = self.line
        if self.suggestion:
            d["suggestion"] = self.suggestion
        return d


class ReviewResult:
    __slots__ = ("issues", "summary", "file_path", "language")

    def __init__(self) -> None:
        self.issues: List[ReviewIssue] = []
        self.summary: str = ""
        self.file_path: str = ""
        self.language: str = ""

    def to_dict(self) -> Dict[str, Any]:
        sorted_issues = sorted(
            self.issues, key=lambda i: SEVERITY_ORDER.get(i.severity, 99)
        )
        counts = {}
        for issue in sorted_issues:
            counts[issue.severity] = counts.get(issue.severity, 0) + 1
        return {
            "issues": [i.to_dict() for i in sorted_issues],
            "counts": counts,
            "total": len(sorted_issues),
            "summary": self.summary,
            "file": self.file_path,
            "language": self.language,
        }


# ── Static checks ─────────────────────────────────────────────────

_STATIC_CHECKS_JS = [
    {
        "pattern": re.compile(r'\bconsole\.(log|warn|error|debug|info)\s*\('),
        "severity": SEVERITY_LOW,
        "title": "Console statement found",
        "explanation": "Console statements should not be left in production code. Use a proper logging library instead.",
        "suggestion": "Remove or replace with a structured logger (e.g., winston, pino).",
    },
    {
        "pattern": re.compile(r'\beval\s*\('),
        "severity": SEVERITY_CRITICAL,
        "title": "Use of eval() detected",
        "explanation": "eval() executes arbitrary code and is a major security risk. It can lead to code injection vulnerabilities.",
        "suggestion": "Replace eval() with JSON.parse() for data, or use a safe alternative for dynamic code execution.",
    },
    {
        "pattern": re.compile(r'\bnew\s+Function\s*\('),
        "severity": SEVERITY_HIGH,
        "title": "Dynamic function constructor detected",
        "explanation": "new Function() is similar to eval() and can introduce code injection risks.",
        "suggestion": "Avoid dynamic function creation. Use named functions or closures instead.",
    },
    {
        "pattern": re.compile(r'(?:^|\s)var\s+'),
        "severity": SEVERITY_LOW,
        "title": "var declaration used",
        "explanation": "var has function scope and can lead to unexpected hoisting behavior. Use const or let instead.",
        "suggestion": "Replace var with const (preferred) or let where reassignment is needed.",
    },
    {
        "pattern": re.compile(r'catch\s*\(\s*\w+\s*\)\s*\{\s*\}'),
        "severity": SEVERITY_MEDIUM,
        "title": "Empty catch block",
        "explanation": "Swallowing exceptions silently hides errors and makes debugging difficult.",
        "suggestion": "At minimum, log the error. Consider re-throwing or handling it appropriately.",
    },
    {
        "pattern": re.compile(r'==(?!=)'),
        "severity": SEVERITY_LOW,
        "title": "Loose equality (==) used",
        "explanation": "Loose equality performs type coercion which can lead to unexpected results.",
        "suggestion": "Use strict equality (===) and strict inequality (!==) instead.",
    },
    {
        "pattern": re.compile(r'!=(?!=)'),
        "severity": SEVERITY_LOW,
        "title": "Loose inequality (!=) used",
        "explanation": "Loose inequality performs type coercion which can lead to unexpected results.",
        "suggestion": "Use strict equality (===) and strict inequality (!==) instead.",
    },
    {
        "pattern": re.compile(r'(?:TODO|FIXME|HACK|XXX)\b', re.IGNORECASE),
        "severity": SEVERITY_LOW,
        "title": "Unresolved TODO/FIXME comment",
        "explanation": "This comment indicates incomplete or temporary code that should be addressed.",
        "suggestion": "Resolve the TODO/FIXME before merging, or convert it to a tracked issue.",
    },
    {
        "pattern": re.compile(r'await\s+.*\n.*await\s+', re.MULTILINE),
        "severity": SEVERITY_MEDIUM,
        "title": "Potential sequential awaits",
        "explanation": "Multiple sequential await statements may indicate missed opportunities for parallelization.",
        "suggestion": "Consider using Promise.all() or Promise.allSettled() for independent async operations.",
    },
    {
        "pattern": re.compile(r'(?:password|secret|api_?key|token)\s*[:=]\s*["\'][^"\']+["\']', re.IGNORECASE),
        "severity": SEVERITY_CRITICAL,
        "title": "Hardcoded secret detected",
        "explanation": "Secrets or credentials appear to be hardcoded in source code. This is a serious security vulnerability.",
        "suggestion": "Move secrets to environment variables or a secrets manager. Never commit secrets to version control.",
    },
]

_STATIC_CHECKS_PYTHON = [
    {
        "pattern": re.compile(r'\bexcept\s*:'),
        "severity": SEVERITY_HIGH,
        "title": "Bare except clause",
        "explanation": "Bare except catches all exceptions including SystemExit and KeyboardInterrupt, which should generally not be caught.",
        "suggestion": "Catch specific exceptions (e.g., except ValueError:) or use 'except Exception:' at minimum.",
    },
    {
        "pattern": re.compile(r'\beval\s*\('),
        "severity": SEVERITY_CRITICAL,
        "title": "Use of eval() detected",
        "explanation": "eval() executes arbitrary code and is a major security risk.",
        "suggestion": "Replace with ast.literal_eval() for data parsing, or redesign the logic.",
    },
    {
        "pattern": re.compile(r'\bexec\s*\('),
        "severity": SEVERITY_CRITICAL,
        "title": "Use of exec() detected",
        "explanation": "exec() executes arbitrary code and is a major security risk.",
        "suggestion": "Avoid dynamic code execution. Use safer alternatives.",
    },
    {
        "pattern": re.compile(r'(?:TODO|FIXME|HACK|XXX)\b', re.IGNORECASE),
        "severity": SEVERITY_LOW,
        "title": "Unresolved TODO/FIXME comment",
        "explanation": "This comment indicates incomplete or temporary code.",
        "suggestion": "Resolve before merging or convert to a tracked issue.",
    },
    {
        "pattern": re.compile(r'(?:password|secret|api_?key|token)\s*[:=]\s*["\'][^"\']+["\']', re.IGNORECASE),
        "severity": SEVERITY_CRITICAL,
        "title": "Hardcoded secret detected",
        "explanation": "Secrets appear to be hardcoded in source code.",
        "suggestion": "Use environment variables or a secrets manager.",
    },
    {
        "pattern": re.compile(r'\bimport\s+\*\s*$'),
        "severity": SEVERITY_MEDIUM,
        "title": "Wildcard import used",
        "explanation": "Wildcard imports pollute the namespace and make it unclear which names are used.",
        "suggestion": "Import specific names: from module import name1, name2.",
    },
    {
        "pattern": re.compile(r'mutable.*default|def\s+\w+\s*\([^)]*=\s*\[\]|def\s+\w+\s*\([^)]*=\s*\{\}'),
        "severity": SEVERITY_HIGH,
        "title": "Mutable default argument",
        "explanation": "Mutable default arguments (list, dict) are shared across all calls and can cause subtle bugs.",
        "suggestion": "Use None as default and create the mutable object inside the function body.",
    },
]

_LANG_CHECKS = {
    "TypeScript": _STATIC_CHECKS_JS,
    "JavaScript": _STATIC_CHECKS_JS,
    "Python": _STATIC_CHECKS_PYTHON,
}


def run_static_checks(code: str, language: str, file_path: str = "") -> List[ReviewIssue]:
    issues: List[ReviewIssue] = []
    checks = _LANG_CHECKS.get(language, _STATIC_CHECKS_JS)

    lines = code.split("\n")
    for line_num, line in enumerate(lines, 1):
        for check in checks:
            if check["pattern"].search(line):
                issues.append(ReviewIssue(
                    severity=check["severity"],
                    title=check["title"],
                    explanation=check["explanation"],
                    file=file_path,
                    line=line_num,
                    suggestion=check.get("suggestion", ""),
                    source="static",
                ))

    if language in ("TypeScript", "JavaScript", "JSX", "TSX"):
        fn_pattern = re.compile(
            r'(?:export\s+)?(?:async\s+)?function\s+\w+|(?:export\s+)?(?:const|let|var)\s+\w+\s*=\s*(?:async\s+)?(?:\([^)]*\)|[^=])\s*=>',
        )
        for line_num, line in enumerate(lines, 1):
            if fn_pattern.search(line):
                indent = len(line) - len(line.lstrip())
                func_lines = 0
                for inner_line in lines[line_num:]:
                    inner_indent = len(inner_line) - len(inner_line.lstrip())
                    if inner_line.strip() and inner_indent < indent and func_lines > 0:
                        break
                    if inner_line.strip():
                        func_lines += 1
                if func_lines > 50:
                    issues.append(ReviewIssue(
                        severity=SEVERITY_MEDIUM,
                        title="Long function detected",
                        explanation=f"Function is {func_lines} lines long. Long functions are harder to test, read, and maintain.",
                        file=file_path,
                        line=line_num,
                        suggestion="Consider breaking this function into smaller, focused functions.",
                        source="static",
                    ))

    return issues


# ── Repository context ────────────────────────────────────────────

def _build_repo_context(
    nodes: List[Dict[str, Any]],
    rels: List[Dict[str, Any]],
    file_path: str,
    entity_name: str = "",
) -> str:
    parts = []

    file_nodes = [n for n in nodes if (n.get("file_path") or n.get("path", "")) == file_path]
    if file_nodes:
        parts.append("ENTITIES IN THIS FILE:")
        for n in file_nodes[:15]:
            label = n.get("label", "?")
            name = n.get("name", "?")
            parts.append(f"  [{label}] {name}")

    node_ids = {n.get("node_id") for n in file_nodes}
    if node_ids:
        incoming = [r for r in rels if r.get("to_id") in node_ids]
        outgoing = [r for r in rels if r.get("from_id") in node_ids]
        if incoming:
            parts.append("\nWHO CALLS/USES THIS FILE:")
            for r in incoming[:10]:
                parts.append(f"  {r.get('from_name', '?')} --[{r.get('type', '?')}]--> {r.get('to_name', '?')}")
        if outgoing:
            parts.append("\nTHIS FILE DEPENDS ON:")
            for r in outgoing[:10]:
                parts.append(f"  {r.get('from_name', '?')} --[{r.get('type', '?')}]--> {r.get('to_name', '?')}")

    related_files = set()
    for r in rels:
        from_fp = r.get("from_id", "").split(":")[2] if ":" in r.get("from_id", "") else ""
        to_fp = r.get("to_id", "").split(":")[2] if ":" in r.get("to_id", "") else ""
        if from_fp == file_path and to_fp:
            related_files.add(to_fp)
        elif to_fp == file_path and from_fp:
            related_files.add(from_fp)
    if related_files:
        parts.append(f"\nRELATED FILES ({len(related_files)}):")
        for fp in sorted(related_files)[:5]:
            parts.append(f"  {fp}")

    return "\n".join(parts)


# ── AI review ─────────────────────────────────────────────────────

REVIEW_SYSTEM_PROMPT = """You are DevPilot AI Code Reviewer. You perform thorough code reviews.

RULES:
1. Distinguish between CONFIRMED issues (clear evidence in the code) and SUGGESTIONS (potential improvements, style, best practices).
2. Use "source": "static" for confirmed/static findings. Use "source": "ai" for AI suggestions.
3. Do NOT claim something is definitely a bug if the evidence is uncertain. Use phrases like "may cause", "could lead to", "consider".
4. Severity levels: CRITICAL (security, data loss), HIGH (bugs, significant issues), MEDIUM (code quality, maintainability), LOW (style, minor improvements).
5. Every issue MUST have a title, explanation, and suggestion.
6. If provided with repo context, consider how this code fits into the larger system.
7. Be specific about line numbers when possible.
8. Return ONLY a JSON array of issues. No other text.

{static_findings}

REPOSITORY CONTEXT:
{repo_context}

CODE TO REVIEW ({file_path}):
```{language}
{code}
```

Return a JSON array of review issues. Each issue:
{{
  "severity": "CRITICAL|HIGH|MEDIUM|LOW",
  "title": "short title",
  "explanation": "detailed explanation",
  "file": "{file_path}",
  "line": null or line_number,
  "suggestion": "actionable suggestion",
  "source": "static or ai"
}}

Return ONLY the JSON array, nothing else."""


async def ai_review(
    code: str,
    language: str,
    file_path: str,
    entity_name: str = "",
    nodes: Optional[List[Dict[str, Any]]] = None,
    rels: Optional[List[Dict[str, Any]]] = None,
) -> str:
    static_issues = run_static_checks(code, language, file_path)

    static_findings_text = ""
    if static_issues:
        static_findings_text = "STATIC ANALYSIS FINDINGS (already confirmed):\n"
        for issue in static_issues:
            line_info = f" line {issue.line}" if issue.line else ""
            static_findings_text += f"- [{issue.severity}] {issue.title}{line_info}: {issue.explanation}\n"
    else:
        static_findings_text = "No static analysis issues found."

    repo_context = ""
    if nodes is not None and rels is not None:
        repo_context = _build_repo_context(nodes, rels, file_path, entity_name)
    if not repo_context:
        repo_context = "No repository context available."

    prompt = REVIEW_SYSTEM_PROMPT.format(
        static_findings=static_findings_text,
        repo_context=repo_context,
        file_path=file_path,
        language=language,
        code=code[:12000],
    )

    try:
        response = await _call_llm(
            [{"role": "user", "content": prompt}],
            temperature=0.2,
        )
    except RuntimeError:
        return json.dumps([i.to_dict() for i in static_issues])

    ai_issues = _parse_ai_response(response, file_path)

    all_issues = static_issues + ai_issues
    return json.dumps([i.to_dict() for i in all_issues])


def _parse_ai_response(response: str, file_path: str) -> List[ReviewIssue]:
    text = response.strip()
    if text.startswith("```"):
        text = re.sub(r'^```\w*\n?', '', text)
        text = re.sub(r'\n?```$', '', text)

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
            except json.JSONDecodeError:
                return []
        else:
            return []

    if not isinstance(data, list):
        return []

    issues = []
    for item in data:
        if not isinstance(item, dict):
            continue
        severity = item.get("severity", "LOW").upper()
        if severity not in SEVERITY_ORDER:
            severity = SEVERITY_LOW
        issues.append(ReviewIssue(
            severity=severity,
            title=item.get("title", "Untitled issue"),
            explanation=item.get("explanation", ""),
            file=item.get("file", file_path),
            line=item.get("line"),
            suggestion=item.get("suggestion", ""),
            source=item.get("source", "ai"),
        ))
    return issues


# ── Main pipeline ─────────────────────────────────────────────────

async def review_code(
    code: str,
    language: str,
    file_path: str,
    entity_name: str = "",
    diff: str = "",
    nodes: Optional[List[Dict[str, Any]]] = None,
    rels: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    review_code_text = code
    if diff:
        review_code_text = f"{code}\n\n--- DIFF (changes to review) ---\n{diff}"

    issues_json = await ai_review(review_code_text, language, file_path, entity_name, nodes, rels)
    issues = json.loads(issues_json)

    static_count = sum(1 for i in issues if i.get("source") == "static")
    ai_count = sum(1 for i in issues if i.get("source") == "ai")
    critical = sum(1 for i in issues if i.get("severity") == "CRITICAL")
    high = sum(1 for i in issues if i.get("severity") == "HIGH")

    if critical > 0:
        summary = f"Found {len(issues)} issues including {critical} critical. Review required before merge."
    elif high > 0:
        summary = f"Found {len(issues)} issues including {high} high severity. Please address before merging."
    elif len(issues) > 0:
        summary = f"Found {len(issues)} issues ({static_count} static, {ai_count} AI suggestions). Consider addressing."
    else:
        summary = "No issues found. Code looks good!"

    return {
        "issues": issues,
        "counts": {
            "CRITICAL": critical,
            "HIGH": high,
            "MEDIUM": sum(1 for i in issues if i.get("severity") == "MEDIUM"),
            "LOW": sum(1 for i in issues if i.get("severity") == "LOW"),
        },
        "total": len(issues),
        "static_count": static_count,
        "ai_count": ai_count,
        "summary": summary,
        "file": file_path,
        "language": language,
    }
