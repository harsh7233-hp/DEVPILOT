"""Finding persistence + false-positive management.

Findings from each deep scan are persisted to ``data/security/{rid}.json``.
Manual review statuses are stored per finding fingerprint and survive
re-scans: when a new scan produces the same fingerprint, the previous human
decision is re-applied. Original evidence is NEVER deleted — status changes
only annotate findings (open / false_positive / accepted_risk /
needs_review / resolved), preserving the audit trail with a note + timestamp.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional

from app.services.intelligence import repo_id as make_repo_id

_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
_SEC_DIR = os.path.join(_DATA_DIR, "security")

VALID_STATUSES = {"open", "false_positive", "accepted_risk", "needs_review", "resolved"}
STATUS_LABELS = {
    "open": "Open",
    "false_positive": "False Positive",
    "accepted_risk": "Accepted Risk",
    "needs_review": "Needs Review",
    "resolved": "Resolved",
}


def _sec_path(rid: str) -> str:
    return os.path.join(_SEC_DIR, f"{rid}.json")


def save_security_report(rid: str, report: Dict[str, Any]) -> None:
    try:
        os.makedirs(_SEC_DIR, exist_ok=True)
        with open(_sec_path(rid), "w") as fh:
            json.dump(report, fh)
    except Exception:
        pass


def load_security_report(rid: str) -> Optional[Dict[str, Any]]:
    try:
        with open(_sec_path(rid)) as fh:
            return json.load(fh)
    except Exception:
        return None


def load_status_overrides(rid: str) -> Dict[str, Dict[str, Any]]:
    report = load_security_report(rid)
    return (report or {}).get("status_overrides", {})


def set_finding_status(
    rid: str,
    fingerprint: str,
    status: str,
    note: str = "",
) -> Optional[Dict[str, Any]]:
    """Record a review decision. Returns the updated override entry."""
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status '{status}'. Valid: {sorted(VALID_STATUSES)}")
    report = load_security_report(rid) or {}
    overrides: Dict[str, Dict[str, Any]] = report.get("status_overrides", {})
    prev = overrides.get(fingerprint, {})
    entry = {
        "status": status,
        "note": note,
        "updated_at": int(time.time()),
        "previous_status": prev.get("status", "open"),
        # preserve the original evidence reference — never deleted
        "original_evidence_ref": prev.get("original_evidence_ref")
        or _find_evidence_ref(report, fingerprint),
    }
    overrides[fingerprint] = entry
    report["status_overrides"] = overrides
    save_security_report(rid, report)
    return entry


def _find_evidence_ref(report: Dict[str, Any], fingerprint: str) -> Optional[Dict[str, Any]]:
    for f in report.get("findings", []):
        if f.get("fingerprint") == fingerprint:
            return {"file": f.get("file"), "line": f.get("line"),
                    "rule_id": f.get("rule_id"), "title": f.get("title")}
    return None


def apply_statuses(
    findings: List[Dict[str, Any]],
    overrides: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Merge stored review decisions onto freshly scanned findings."""
    out = []
    for f in findings:
        merged = dict(f)
        entry = overrides.get(f.get("fingerprint", ""))
        if entry:
            merged["status"] = entry["status"]
            merged["status_note"] = entry.get("note", "")
            merged["status_updated_at"] = entry.get("updated_at")
            merged["review_history"] = [entry]
        else:
            merged.setdefault("status", "open")
        out.append(merged)
    return out
