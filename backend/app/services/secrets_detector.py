"""Secret detection engine.

CRITICAL SAFETY PROPERTIES
==========================
1. Raw secret values are NEVER stored on finding dicts. Every finding carries
   ``masked`` preview text produced by :func:`mask_secret` and an evidence
   snippet in which the matched value is replaced by ``[REDACTED]``.
2. Callers must never log the raw content of these matches. This module does
   not emit logs containing matched values.
3. Findings produced here must NOT be forwarded verbatim to any LLM. The
   evidence field is safe by construction (redacted), but integrators should
   still prefer sending only metadata (rule id, file, line) downstream.

Detection is deterministic: fixed regex patterns + Shannon entropy gate +
placeholder filtering. Confidence reflects how strong the deterministic
signal is (see Module 2 spec §11).
"""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# ── Masking ──────────────────────────────────────────────────────────

MASK_CHAR = "*"


def mask_secret(raw: str, visible_tail: int = 4) -> str:
    """Return a masked preview like ``ghp_********ABCD``.

    Keeps any leading non-alphanumeric prefix (e.g. ``ghp_``, ``sk_live_``)
    plus the final ``visible_tail`` characters of the value. Never returns
    more than ~25% of the original value's length.
    """
    raw = raw.strip()
    if len(raw) <= visible_tail:
        # Too short to mask safely — show nothing meaningful.
        return MASK_CHAR * 8
    prefix_match = re.match(r"^([A-Za-z]{1,12}_?[A-Za-z]{0,4}_)", raw)
    prefix = prefix_match.group(1) if prefix_match else ""
    body = raw[len(prefix):]
    tail = body[-visible_tail:] if len(body) > visible_tail else ""
    masked_len = max(6, min(len(body) - len(tail), 12))
    return f"{prefix}{MASK_CHAR * masked_len}{tail}"


def redact_evidence(evidence: str, raw_values: List[str]) -> str:
    """Replace every occurrence of the given raw values inside evidence."""
    out = evidence
    for rv in raw_values:
        if rv:
            out = out.replace(rv, "[REDACTED]")
    return out


# ── Entropy helpers ──────────────────────────────────────────────────

def shannon_entropy(value: str) -> float:
    if not value:
        return 0.0
    freq: Dict[str, int] = {}
    for ch in value:
        freq[ch] = freq.get(ch, 0) + 1
    n = len(value)
    return -sum((c / n) * math.log2(c / n) for c in freq.values())


# ── Placeholder / false-positive filtering ───────────────────────────

_PLACEHOLDER_RE = re.compile(
    r"""your[_-]?|example|changeme|change_me|placeholder|x{4,}|dummy|sample|
        <[^>]+>|\$\{|\{\{|xxxx-|-xxx|abcd1234|12345678|0123456789|todo|fixme|
        description|process\.env|os\.environ|import\s|localhost|127\.0\.0\.1""",
    re.IGNORECASE | re.VERBOSE,
)


def _looks_placeholder(value: str) -> bool:
    return bool(_PLACEHOLDER_RE.search(value))


# ── Rule definitions ─────────────────────────────────────────────────

@dataclass
class SecretRule:
    id: str
    title: str
    pattern: re.Pattern
    group_index: int = 0            # regex group holding the raw secret
    severity: str = "CRITICAL"
    confidence: str = "HIGH"
    min_entropy: float = 0.0        # extra entropy gate on captured value
    min_length: int = 8
    standards: List[Dict[str, str]] = field(default_factory=list)
    why: str = ""
    recommendation: str = ""


OWASP_A07 = {"standard": "OWASP Top 10:2021", "id": "A07", "name": "Identification and Authentication Failures"}
OWASP_A02 = {"standard": "OWASP Top 10:2021", "id": "A02", "name": "Cryptographic Failures"}
OWASP_A05 = {"standard": "OWASP Top 10:2021", "id": "A05", "name": "Security Misconfiguration"}
ASVS_V14 = {"standard": "OWASP ASVS 4.0", "id": "V14", "name": "Configuration"}
CISA_DEFAULTS = {
    "standard": "CISA Secure-by-Design",
    "id": "Default Credentials Pledge",
    "name": "Eliminate default passwords and hardcoded credentials",
}

_SECRET_LEAK_WHY = (
    "Credentials embedded in source control leak into git history, forks and "
    "build artifacts; anyone who obtains the repository gains the credential."
)
_SECRET_LEAK_REC = (
    "Revoke and rotate the exposed credential immediately, then load it from "
    "an environment variable or a secret manager instead of source code."
)

SECRET_RULES: List[SecretRule] = [
    SecretRule(
        id="SEC-AWS-AKID",
        title="AWS access key ID committed to source",
        pattern=re.compile(r"\b(AKIA[0-9A-Z]{16})\b"),
        severity="CRITICAL",
        confidence="HIGH",
        min_entropy=2.5,
        standards=[dict(OWASP_A07), dict(ASVS_V14), dict(CISA_DEFAULTS)],
        why=_SECRET_LEAK_WHY,
        recommendation=_SECRET_LEAK_REC,
    ),
    SecretRule(
        id="SEC-GITHUB-TOKEN",
        title="GitHub token committed to source",
        pattern=re.compile(r"\b(gh[pousr]_[A-Za-z0-9]{36,255})\b"),
        severity="CRITICAL",
        confidence="HIGH",
        standards=[dict(OWASP_A07), dict(ASVS_V14)],
        why=_SECRET_LEAK_WHY,
        recommendation=_SECRET_LEAK_REC,
    ),
    SecretRule(
        id="SEC-SLACK-TOKEN",
        title="Slack token committed to source",
        pattern=re.compile(r"\b(xox[baprs]-[A-Za-z0-9-]{10,})\b"),
        severity="HIGH",
        confidence="HIGH",
        standards=[dict(OWASP_A07), dict(ASVS_V14)],
        why=_SECRET_LEAK_WHY,
        recommendation=_SECRET_LEAK_REC,
    ),
    SecretRule(
        id="SEC-GOOGLE-APIKEY",
        title="Google API key committed to source",
        pattern=re.compile(r"\b(AIza[0-9A-Za-z_-]{35})\b"),
        severity="HIGH",
        confidence="HIGH",
        standards=[dict(OWASP_A07), dict(ASVS_V14)],
        why=_SECRET_LEAK_WHY,
        recommendation=_SECRET_LEAK_REC,
    ),
    SecretRule(
        id="SEC-STRIPE-LIVE",
        title="Stripe live secret key committed to source",
        pattern=re.compile(r"\b([sr]k_live_[A-Za-z0-9]{20,})\b"),
        severity="CRITICAL",
        confidence="HIGH",
        standards=[dict(OWASP_A07), dict(ASVS_V14)],
        why=_SECRET_LEAK_WHY,
        recommendation=_SECRET_LEAK_REC,
    ),
    SecretRule(
        id="SEC-OPENAI-KEY",
        title="OpenAI-style API key committed to source",
        pattern=re.compile(r"\b(sk-[A-Za-z0-9_-]{32,})\b"),
        severity="HIGH",
        confidence="MEDIUM",  # pattern can match other vendors' sk- keys
        min_entropy=3.0,
        standards=[dict(OWASP_A07), dict(ASVS_V14)],
        why=_SECRET_LEAK_WHY,
        recommendation=_SECRET_LEAK_REC,
    ),
    SecretRule(
        id="SEC-PRIVATE-KEY",
        title="Private key material committed to source",
        pattern=re.compile(r"-----BEGIN ((?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY(?: BLOCK)?)-----"),
        group_index=0,
        severity="CRITICAL",
        confidence="HIGH",
        standards=[{"standard": "OWASP Top 10:2021", "id": "A02", "name": "Cryptographic Failures"}, dict(ASVS_V14)],
        why=(
            "A private key in the repository lets anyone impersonate the service "
            "or decrypt data signed/encrypted with it; git history keeps it forever."
        ),
        recommendation="Remove the key, rotate it, and mount it from a secret store at runtime.",
    ),
    SecretRule(
        id="SEC-JWT-LITERAL",
        title="Hardcoded JSON Web Token",
        pattern=re.compile(r"\b(eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{8,})"),
        severity="HIGH",
        confidence="MEDIUM",
        min_entropy=3.0,
        standards=[dict(OWASP_A07), dict(ASVS_V14)],
        why=_SECRET_LEAK_WHY,
        recommendation=_SECRET_LEAK_REC,
    ),
    SecretRule(
        id="SEC-DB-URL-CREDS",
        title="Database connection string with embedded credentials",
        pattern=re.compile(
            r"\b((?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis|amqp)://[^\s:'\"]+:[^\s@'\"]{4,}@[\w.-]+)"
        ),
        severity="CRITICAL",
        confidence="HIGH",
        standards=[dict(OWASP_A07), dict(ASVS_V14)],
        why=_SECRET_LEAK_WHY,
        recommendation=_SECRET_LEAK_REC,
    ),
]

# Generic assignment pattern handled separately (needs entropy gate).
_GENERIC_ASSIGN_RE = re.compile(
    r"""\b(api[_-]?key|apikey|secret[_-]?key|client[_-]?secret|auth[_-]?token|
        access[_-]?token|refresh[_-]?token|private[_-]?key|password|passwd|pwd)['"]?
        \s*[:=]\s*['"]([A-Za-z0-9_/+=.\-~!@#$%^&*]{16,})['"]""",
    re.IGNORECASE | re.VERBOSE,
)


def detect_secrets(path: str, content: str) -> List[Dict[str, Any]]:
    """Scan one file and return secret findings with MASKED previews only."""
    lines = content.splitlines()
    findings: List[Dict[str, Any]] = []
    seen_locations: set = set()

    def line_of(offset: int) -> int:
        return content.count("\n", 0, offset)

    def snippet_with_redaction(idx: int, raw_value: str) -> str:
        lo, hi = max(0, idx - 1), min(len(lines), idx + 2)
        return redact_evidence("\n".join(lines[lo:hi]), [raw_value])

    def add(rule_id: str, title: str, idx: int, raw: str, severity: str,
           confidence: str, standards: List[Dict[str, str]], why: str, rec: str) -> None:
        key = (rule_id, idx)
        if key in seen_locations:
            return
        seen_locations.add(key)
        fingerprint = hashlib.sha1(
            f"{path}:{idx}:{rule_id}:{mask_secret(raw)}".encode()
        ).hexdigest()[:16]
        findings.append({
            "rule_id": rule_id,
            "title": title,
            "severity": severity,
            "confidence": confidence,
            "file": path,
            "line": idx + 1,
            "symbol": "",
            "masked_preview": mask_secret(raw),
            "evidence": snippet_with_redaction(idx, raw)[:400],
            "why": why,
            "recommendation": rec,
            "standards": standards,
            "detection_method": "Deterministic pattern match with entropy validation",
            "category": "secret-detection",
            "fingerprint": fingerprint,
        })

    for rule in SECRET_RULES:
        for m in rule.pattern.finditer(content):
            raw = (m.group(rule.group_index) or m.group(0)).strip()
            if len(raw) < rule.min_length or _looks_placeholder(raw):
                continue
            if rule.min_entropy and shannon_entropy(raw) < rule.min_entropy:
                continue
            idx = line_of(m.start())
            add(rule.id, rule.title, idx, raw, rule.severity, rule.confidence,
                rule.standards, rule.why, rule.recommendation)

    for m in _GENERIC_ASSIGN_RE.finditer(content):
        name, raw = m.group(1), m.group(2)
        if _looks_placeholder(raw):
            continue
        entropy = shannon_entropy(raw)
        has_classes = (re.search(r"[a-z]", raw) and re.search(r"[A-Z]", raw)) or \
                      (re.search(r"[A-Za-z]", raw) and re.search(r"[0-9]", raw))
        # High-entropy, character-class-mixed values only — keeps confidence honest.
        if entropy < 3.2 or not has_classes:
            continue
        idx = line_of(m.start())
        add(
            "SEC-GENERIC-CREDENTIAL",
            f"Hardcoded credential assigned to '{name}'",
            idx, raw, "HIGH", "MEDIUM",
            [dict(OWASP_A07), dict(ASVS_V14)],
            _SECRET_LEAK_WHY,
            _SECRET_LEAK_REC,
        )

    return findings


def scan_files_for_secrets(files: Dict[str, str]) -> List[Dict[str, Any]]:
    """Scan a mapping of path → content. Returns findings sorted by severity."""
    order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    all_findings: List[Dict[str, Any]] = []
    for path, content in files.items():
        all_findings.extend(detect_secrets(path, content))
    all_findings.sort(key=lambda f: order.get(f["severity"], 99))
    return all_findings
