"""Deterministic security rules engine.

Pipeline (Module 2 spec §6):

    Repository → Parser → Security Rules → Evidence → Confidence
      → Severity → Standards Mapping → Security Posture → AI Explanation

Every rule is a fixed pattern (regex) evaluated against file content. Rules
declare the languages/filenames they apply to so only relevant checks run for
the detected stack. A rule produces findings with:

- ``evidence``   : matched line + surrounding snippet from the real file
- ``confidence`` : HIGH  = strong deterministic evidence (exact config value,
                          well-known credential format, unambiguous API call)
                   MEDIUM= strong indication but incomplete evidence (pattern
                          present but exploitability depends on data flow)
                   LOW   = heuristic / potential issue
- ``standards``  : only mappings that are confidently established. Empty list
                   means the UI must display ``Standard mapping unavailable``.

Rules never invent requirement IDs. Severity is assigned per-rule statically.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

# ── Standards references (only confidently established mappings) ─────

def owasp(id_: str, name: str) -> Dict[str, str]:
    return {"standard": "OWASP Top 10:2021", "id": id_, "name": name}


def asvs(chapter: str, name: str) -> Dict[str, str]:
    return {"standard": "OWASP ASVS 4.0", "id": chapter, "name": name}


A01 = lambda: owasp("A01", "Broken Access Control")
A02 = lambda: owasp("A02", "Cryptographic Failures")
A03 = lambda: owasp("A03", "Injection")
A05 = lambda: owasp("A05", "Security Misconfiguration")
A06 = lambda: owasp("A06", "Vulnerable and Outdated Components")
A07 = lambda: owasp("A07", "Identification and Authentication Failures")
A08 = lambda: owasp("A08", "Software and Data Integrity Failures")
A09 = lambda: owasp("A09", "Security Logging and Monitoring Failures")
A10 = lambda: owasp("A10", "Server-Side Request Forgery (SSRF)")
V2 = lambda: asvs("V2", "Authentication")
V4 = lambda: asvs("V4", "Access Control")
V5 = lambda: asvs("V5", "Validation, Sanitization and Output Encoding")
V6 = lambda: asvs("V6", "Stored Cryptography")
V7 = lambda: asvs("V7", "Error Handling and Logging")
V9 = lambda: asvs("V9", "Communication")
V14 = lambda: asvs("V14", "Configuration")


@dataclass
class SecurityRule:
    id: str
    title: str
    category: str                 # injection | xss | crypto | auth | config | ...
    severity: str                 # CRITICAL | HIGH | MEDIUM | LOW
    confidence: str               # HIGH | MEDIUM | LOW
    pattern: re.Pattern
    langs: Optional[Set[str]] = None          # None = all languages
    filename_re: Optional[re.Pattern] = None  # e.g. settings.py only
    why: str = ""
    recommendation: str = ""
    detection_method: str = "Regex pattern match on source content"
    standards: List[Dict[str, str]] = field(default_factory=list)
    manual_review_required: bool = False


RULES: List[SecurityRule] = [
    # ── Injection family ─────────────────────────────────────────────
    SecurityRule(
        id="PY-SQL-FSTRING",
        title="SQL query constructed with an f-string (possible SQL injection)",
        category="injection",
        severity="HIGH", confidence="MEDIUM",
        pattern=re.compile(
            r"""f['"](?:\s*)(SELECT|INSERT|UPDATE|DELETE|DROP)\b[^'"]*\{""",
        ),
        langs={"Python"},
        why="String-formatted SQL lets user-controlled values change query semantics; attackers can read, modify or destroy data.",
        recommendation="Use parameterized queries / bound arguments provided by your database driver or ORM.",
        standards=[A03(), V5()],
    ),
    SecurityRule(
        id="JS-SQL-CONCAT",
        title="SQL query built via string concatenation/template literal",
        category="injection",
        severity="HIGH", confidence="MEDIUM",
        pattern=re.compile(
            r"""(?:query|sql|execute|raw)\s*\(\s*[`'"](SELECT|INSERT|UPDATE|DELETE)\b[^`'"]*(?:\$\{|['"]\s*\+)""",
            re.IGNORECASE,
        ),
        langs={"JavaScript", "TypeScript"},
        why="Concatenated SQL allows user input to alter the query; a classic injection vector.",
        recommendation="Use parameter placeholders ($1, ?, :name) supported by the driver/ORM.",
        standards=[A03(), V5()],
    ),
    SecurityRule(
        id="PY-CMD-SHELLTRUE",
        title="subprocess call with shell=True",
        category="command-injection",
        severity="CRITICAL", confidence="MEDIUM",
        pattern=re.compile(r"subprocess\.(?:run|call|check_call|check_output|Popen)\([^)]*shell\s*=\s*True"),
        langs={"Python"},
        why="shell=True passes the command through the system shell; metacharacters in any interpolated value allow arbitrary command execution.",
        recommendation="Pass the command as a list without shell=True, or validate/allow-list every argument.",
        standards=[A03(), V5()], manual_review_required=True,
    ),
    SecurityRule(
        id="PY-OS-SYSTEM",
        title="os.system / os.popen executes a shell command",
        category="command-injection",
        severity="HIGH", confidence="MEDIUM",
        pattern=re.compile(r"\bos\.(system|popen)\s*\("),
        langs={"Python"},
        why="Commands executed through the shell interpret metacharacters; dynamic parts enable command injection.",
        recommendation="Prefer subprocess.run([...]) with a static argv list.",
        standards=[A03(), V5()],
    ),
    SecurityRule(
        id="JS-CHILDPROC-EXEC",
        title="child_process.exec with dynamic command string",
        category="command-injection",
        severity="HIGH", confidence="MEDIUM",
        pattern=re.compile(r"child_process\.exec\s*\(|\bexec\s*\(\s*[`'\"]?\s*\$?\{"),
        langs={"JavaScript", "TypeScript"},
        why="exec() runs the string via a shell; interpolated user data can inject commands.",
        recommendation="Use execFile/spawn with an argument array instead of a shell string.",
        standards=[A03(), V5()],
    ),
    SecurityRule(
        id="GEN-EVAL",
        title="Dynamic code evaluation (eval/exec/new Function)",
        category="code-execution",
        severity="HIGH", confidence="MEDIUM",
        pattern=re.compile(r"\beval\s*\(|\bexec\s*\(|new\s+Function\s*\("),
        why="Evaluating strings as code turns any injected value into executable logic.",
        recommendation="Replace with explicit parsing (JSON.parse), mapping lookups, or a restricted interpreter.",
        standards=[A03(), V5()],
    ),
    SecurityRule(
        id="PY-UNSAFE-YAML",
        title="yaml.load without safe Loader (unsafe deserialization)",
        category="deserialization",
        severity="HIGH", confidence="MEDIUM",
        pattern=re.compile(r"yaml\.load\s*\((?![^)]*Loader\s*=)"),
        langs={"Python"},
        why="yaml.load with the default Loader can construct arbitrary Python objects — remote code execution with attacker-controlled YAML.",
        recommendation="Use yaml.safe_load, or pass Loader=yaml.SafeLoader explicitly.",
        standards=[A08(), V5()],
    ),
    SecurityRule(
        id="PY-PICKLE",
        title="Pickle deserialization of potentially untrusted data",
        category="deserialization",
        severity="MEDIUM", confidence="LOW",
        pattern=re.compile(r"\bpickle\.loads?\s*\("),
        langs={"Python"},
        why="Unpickling attacker-controlled bytes executes embedded code. Static scan cannot prove the data is untrusted.",
        recommendation="Use JSON or another data-only format for anything crossing a trust boundary.",
        standards=[A08(), V5()], manual_review_required=True,
    ),
    SecurityRule(
        id="JS-NODE-SERIALIZE",
        title="node-serialize unserialize() (known RCE-prone deserialization)",
        category="deserialization",
        severity="HIGH", confidence="MEDIUM",
        pattern=re.compile(r"\bunserialize\s*\("),
        langs={"JavaScript", "TypeScript"},
        why="The popular node-serialize package can instantiate functions from payloads, enabling code execution.",
        recommendation="Avoid serializing functions; prefer JSON with schema validation.",
        standards=[A08(), V5()],
    ),

    # ── XSS ──────────────────────────────────────────────────────────
    SecurityRule(
        id="JS-INNERHTML",
        title="Assignment to innerHTML / insertAdjacentHTML",
        category="xss",
        severity="HIGH", confidence="MEDIUM",
        pattern=re.compile(r"\.innerHTML\s*=|insertAdjacentHTML\s*\("),
        langs={"JavaScript", "TypeScript"},
        why="Raw HTML assignment executes any script content it carries; if any part is user-derived this becomes XSS.",
        recommendation="Assign textContent, or sanitize with DOMPurify before inserting HTML.",
        standards=[A03(), V5()],
    ),
    SecurityRule(
        id="JS-DANGEROUSLY-SET",
        title="dangerouslySetInnerHTML usage",
        category="xss",
        severity="MEDIUM", confidence="LOW",
        pattern=re.compile(r"dangerouslySetInnerHTML"),
        langs={"TypeScript", "JavaScript"},
        why="Bypasses React's escaping; unsafe if the HTML contains user-supplied content.",
        recommendation="Render text nodes, or sanitize the HTML with DOMPurify first.",
        standards=[A03(), V5()], manual_review_required=True,
    ),
    SecurityRule(
        id="JS-DOC-WRITE",
        title="document.write of dynamic content",
        category="xss",
        severity="MEDIUM", confidence="LOW",
        pattern=re.compile(r"document\.write\s*\("),
        langs={"JavaScript", "TypeScript"},
        why="Writes raw markup into the document; dynamic content can carry scripts.",
        recommendation="Manipulate DOM nodes via createElement/textContent.",
        standards=[A03(), V5()],
    ),

    # ── Crypto / TLS ─────────────────────────────────────────────────
    SecurityRule(
        id="GEN-TLS-DISABLED",
        title="TLS certificate verification disabled",
        category="tls",
        severity="HIGH", confidence="HIGH",
        pattern=re.compile(
            r"verify\s*=\s*False|rejectUnauthorized\s*:\s*false|NODE_TLS_REJECT_UNAUTHORIZED\s*=\s*[\"']?0"
        ),
        why="Skipping certificate validation accepts any certificate, enabling machine-in-the-middle attacks that read or alter traffic.",
        recommendation="Keep verification enabled; trust a custom CA bundle instead of disabling checks.",
        standards=[A02(), V9()],
    ),
    SecurityRule(
        id="PY-WEAK-HASH-PASSWORD",
        title="Weak hash (md5/sha1) used near password handling",
        category="crypto",
        severity="MEDIUM", confidence="MEDIUM",
        pattern=re.compile(
            r"(?:hashlib\.md5|hashlib\.sha1|create_hash\s*\(\s*[\"']md5|createHash\s*\(\s*[\"'](md5|sha1)[\"'])",
        ),
        why="MD5/SHA-1 are broken for password storage; fast hashes allow massive offline cracking.",
        recommendation="Store passwords with argon2id, scrypt or bcrypt.",
        standards=[A02(), V6()],
    ),
    SecurityRule(
        id="GEN-RANDOM-TOKEN",
        title="Math.random/random used where unpredictability matters",
        category="crypto",
        severity="MEDIUM", confidence="LOW",
        pattern=re.compile(
            r"(?:Math\.random\s*\(\s*\)|(?<!\.)\brandom\.random\s*\(\s*\))"
        ),
        why="These generators are predictable; tokens, keys or reset links derived from them can be guessed.",
        recommendation="Use cryptographically secure randomness (crypto.getRandomValues / secrets module).",
        standards=[A02(), V6()], manual_review_required=True,
    ),

    # ── SSRF / path traversal ────────────────────────────────────────
    SecurityRule(
        id="PY-SSRF-REQUEST-ARGS",
        title="Outbound request URL taken directly from request parameters",
        category="ssrf",
        severity="HIGH", confidence="MEDIUM",
        pattern=re.compile(
            r"requests\.(get|post|put|delete|head)\s*\(\s*(request\.(args|form|values|json)|flask\.request)"
        ),
        langs={"Python"},
        why="Fetching a URL supplied by the client lets attackers reach internal services (SSRF).",
        recommendation="Allow-list destination hosts and schemes; resolve DNS and block private ranges.",
        standards=[A10(), V5()], manual_review_required=True,
    ),
    SecurityRule(
        id="JS-SSRF-FETCH-BODY",
        title="fetch() URL built from req body/query",
        category="ssrf",
        severity="HIGH", confidence="MEDIUM",
        pattern=re.compile(r"fetch\s*\(\s*(req|request)\.(body|query|params)\b"),
        langs={"JavaScript", "TypeScript"},
        why="Server-side fetch of a client-controlled URL enables SSRF against internal networks.",
        recommendation="Validate against an allow-list of hosts before requesting.",
        standards=[A10(), V5()], manual_review_required=True,
    ),
    SecurityRule(
        id="PY-PATH-TRAVERSAL",
        title="File access composed from request parameters",
        category="path-traversal",
        severity="HIGH", confidence="MEDIUM",
        pattern=re.compile(
            r"(?:open|send_file|send_from_directory)\s*\(\s*(?:os\.path\.join\s*\(\s*)?(?:request\.(args|form|values)|flask\.request)"
        ),
        langs={"Python"},
        why="User-controlled paths allow ../ traversal to read or overwrite arbitrary files.",
        recommendation="Resolve the final path and assert it stays inside a dedicated base directory.",
        standards=[A01(), V5()],
    ),
    SecurityRule(
        id="JS-PATH-TRAVERSAL",
        title="fs.* path taken from request parameters",
        category="path-traversal",
        severity="HIGH", confidence="MEDIUM",
        pattern=re.compile(
            r"(?:readFile|readFileSync|writeFile|createReadStream)\s*\(\s*(?:req|request)\.(query|params|body)"
        ),
        langs={"JavaScript", "TypeScript"},
        why="Client-controlled filesystem paths enable traversal outside the intended directory.",
        recommendation="Normalize the path and verify the prefix matches the allowed base directory.",
        standards=[A01(), V5()],
    ),

    # ── Auth / session / secrets hygiene ─────────────────────────────
    SecurityRule(
        id="DJANGO-DEBUG-TRUE",
        title="Django DEBUG=True committed",
        category="config",
        severity="MEDIUM", confidence="HIGH",
        pattern=re.compile(r"^\s*DEBUG\s*=\s*True", re.MULTILINE),
        filename_re=re.compile(r"settings.*\.py$|^settings\.py$"),
        langs={"Python"},
        why="Debug mode exposes stack traces, settings and query details to end users.",
        recommendation="Drive DEBUG from an environment variable; default to False in production.",
        standards=[A05(), V14()],
    ),
    SecurityRule(
        id="DJANGO-SECRET-HARDCODED",
        title="Django SECRET_KEY hardcoded",
        category="auth",
        severity="HIGH", confidence="HIGH",
        pattern=re.compile(r"SECRET_KEY\s*=\s*['\"][^'\"${}]{8,}['\"]"),
        filename_re=re.compile(r"settings.*\.py$|^settings\.py$"),
        langs={"Python"},
        why="The secret key signs sessions and password resets; committing it lets attackers forge those values.",
        recommendation="Load SECRET_KEY from the environment and rotate the exposed value.",
        standards=[A07(), V14(), V2()],
    ),
    SecurityRule(
        id="FLASK-DEBUG-TRUE",
        title="Flask debug mode enabled",
        category="config",
        severity="MEDIUM", confidence="HIGH",
        pattern=re.compile(r"app\.run\s*\([^)]*debug\s*=\s*True"),
        langs={"Python"},
        why="The Werkzeug debugger allows remote code execution if reachable in production.",
        recommendation="Disable debug outside development; use a WSGI server in production.",
        standards=[A05(), V14()],
    ),
    SecurityRule(
        id="CORS-WILDCARD-CREDS",
        title="CORS wildcard origin combined with credentials",
        category="config",
        severity="MEDIUM", confidence="MEDIUM",
        pattern=re.compile(
            r"Access-Control-Allow-Origin['\"]?\s*[:=]\s*['\"]\*['\"]|origin\s*:\s*['\"]\*['\"]"
        ),
        why="Any website may call the API; combined with credentials it enables cross-site data theft.",
        recommendation="Echo a strict allow-list of origins instead of '*'.",
        standards=[A05(), V14()],
    ),
    SecurityRule(
        id="ENV-COMMITTED",
        title="Environment file committed to repository",
        category="secrets-hygiene",
        severity="HIGH", confidence="HIGH",
        pattern=None,  # handled structurally by tree check
        why=".env files typically contain real credentials; committing them publishes secrets to everyone with repo access.",
        recommendation="Remove the file from git history, rotate its values, commit only .env.example.",
        standards=[A05(), V14()],
    ),
    SecurityRule(
        id="DOCKER-USER-ROOT",
        title="Container explicitly configured to run as root",
        category="config",
        severity="LOW", confidence="HIGH",
        pattern=re.compile(r"(?m)^USER\s+root\b"),
        filename_re=re.compile(r"Dockerfile[^/]*$"),
        why="Root inside the container widens the blast radius of any application-level compromise.",
        recommendation="Create an unprivileged user and set USER to it.",
        standards=[A05(), V14()],
    ),
    SecurityRule(
        id="GEN-INSECURE-HTTP",
        title="Plain HTTP endpoint referenced",
        category="transport",
        severity="LOW", confidence="HIGH",
        pattern=re.compile(r"http://(?!localhost|127\.0\.0\.1|0\.0\.0\.0|kubernetes\.default)"),
        why="Unencrypted traffic can be read and modified in transit.",
        recommendation="Use https:// endpoints.",
        standards=[A02(), V9()],
    ),
    SecurityRule(
        id="GEN-SENSITIVE-LOG",
        title="Potential logging of sensitive values",
        category="logging",
        severity="LOW", confidence="LOW",
        pattern=re.compile(
            r"(?:console\.(?:log|info|debug)|print|logger?\.\w+)\s*\([^)]*\b(?:password|passwd|token|secret|api[_-]?key)\w*\b",
            re.IGNORECASE,
        ),
        why="Secrets written to logs persist in log aggregation systems and are readable by anyone with log access.",
        recommendation="Log non-sensitive identifiers only; redact credentials before logging.",
        standards=[A09(), V7()], manual_review_required=True,
    ),
]

# Applicable-check bookkeeping -------------------------------------------------

def rule_applicable(rule: SecurityRule, path: str, lang: str) -> bool:
    if rule.pattern is None:
        return False
    if rule.langs is not None and lang not in rule.langs:
        return False
    if rule.filename_re is not None and not rule.filename_re.search(path):
        return False
    return True


def _enclosing_symbol(symbols: List[Tuple[int, int, str]], line_1based: int) -> str:
    for start, end, name in symbols:
        if start <= line_1based <= end:
            return name
    return ""


def scan_file_security(
    path: str, lang: str, content: str,
    symbols: List[Tuple[int, int, str]],
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Run applicable rules over one file.

    Returns ``(findings, executed_rule_ids)`` — executed_rule_ids records which
    checks genuinely ran so posture math reflects real coverage.
    """
    lines = content.splitlines()
    findings: List[Dict[str, Any]] = []
    executed: List[str] = []

    for rule in RULES:
        if rule.id == "ENV-COMMITTED":
            continue  # tree-level rule, applied by caller
        if not rule_applicable(rule, path, lang):
            continue
        executed.append(rule.id)
        for m in rule.pattern.finditer(content):
            idx = content.count("\n", 0, m.start())
            lo, hi = max(0, idx - 1), min(len(lines), idx + 2)
            fingerprint = hashlib.sha1(
                f"{path}:{rule.id}:{m.group(0).strip()[:80]}".encode()
            ).hexdigest()[:16]
            findings.append({
                "rule_id": rule.id,
                "title": rule.title,
                "category": rule.category,
                "severity": rule.severity,
                "confidence": rule.confidence,
                "file": path,
                "line": idx + 1,
                "symbol": _enclosing_symbol(symbols, idx + 1),
                "evidence": "\n".join(lines[lo:hi])[:400],
                "why": rule.why,
                "recommendation": rule.recommendation,
                "standards": [dict(s) for s in rule.standards],
                "detection_method": rule.detection_method,
                "manual_review_required": rule.manual_review_required,
                "source": "static-analysis",
                "category_label": "security",
                "fingerprint": fingerprint,
            })

    # de-duplicate identical rule hits within ±3 lines of each other
    findings.sort(key=lambda f: (f["rule_id"], f["line"]))
    deduped: List[Dict[str, Any]] = []
    last_by_rule: Dict[str, int] = {}
    for f in findings:
        prev = last_by_rule.get(f["rule_id"])
        if prev is not None and abs(prev - f["line"]) <= 3:
            continue
        last_by_rule[f["rule_id"]] = f["line"]
        deduped.append(f)
    return deduped, executed


def env_committed_finding(path: str) -> Dict[str, Any]:
    rule = next(r for r in RULES if r.id == "ENV-COMMITTED")
    fingerprint = hashlib.sha1(f"{path}:ENV-COMMITTED".encode()).hexdigest()[:16]
    return {
        "rule_id": rule.id,
        "title": f"Environment file committed: {path}",
        "category": "secrets-hygiene",
        "severity": rule.severity,
        "confidence": rule.confidence,
        "file": path,
        "line": 1,
        "symbol": "",
        "evidence": f"Repository tree contains {path}",
        "why": rule.why,
        "recommendation": rule.recommendation,
        "standards": [dict(s) for s in rule.standards],
        "detection_method": "Repository tree inspection",
        "manual_review_required": False,
        "source": "static-analysis",
        "category_label": "security",
        "fingerprint": fingerprint,
    }


ENV_FILE_RE = re.compile(r"^\.env($|\.)|(^|/)\.env\.(local|production|staging)$")


def detect_committed_env_files(paths: List[str]) -> List[str]:
    """Return committed .env-style paths (excluding examples/templates)."""
    out = []
    for p in paths:
        base = p.rstrip("/").rsplit("/", 1)[-1]
        if ENV_FILE_RE.match(base) or base == ".env":
            if "example" in base.lower() or "sample" in base.lower() or "template" in base.lower():
                continue
            out.append(p)
    return out
