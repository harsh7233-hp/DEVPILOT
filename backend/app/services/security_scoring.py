"""Evidence-based Security Posture scoring.

FORMULA (also exposed verbatim through ``posture_formula()`` and the API so
the UI can answer "How is Security Posture calculated?"):

    executed_checks : security rules that actually ran against analyzed files
                      (per applicable rule × file executions are aggregated to
                      distinct rules for scoring)
    passed_checks   : executed rules that produced zero open findings
    base            = 100 × passed_checks / executed_checks        (0 if none)
    raw_deduction   = Σ over OPEN findings of
                        points[severity] × confidence_factor[confidence]
                      points: CRITICAL 20 · HIGH 12 · MEDIUM 6 · LOW 2
                      confidence: HIGH 1.0 · MEDIUM 0.6 · LOW 0.25
    deduction       = min(60, raw_deduction)     (cap keeps pass-ratio primary)
    posture         = max(0, round(base − deduction))

Rules:
- Findings with a review status of false_positive, accepted_risk or resolved
  are EXCLUDED from deductions (they remain visible in listings — evidence is
  never deleted).
- If no checks were executable → posture = None ("Not analyzed").
- The score is NOT ``100 − finding_count``; severity and confidence weight it,
  and the base reflects how much of the rule set actually ran.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

SEVERITY_POINTS = {"CRITICAL": 20, "HIGH": 12, "MEDIUM": 6, "LOW": 2}
CONFIDENCE_FACTOR = {"HIGH": 1.0, "MEDIUM": 0.6, "LOW": 0.25}
DEDUCTION_CAP = 60

CLOSED_STATUSES = {"false_positive", "accepted_risk", "resolved"}


def posture_formula() -> Dict[str, Any]:
    return {
        "formula": (
            "posture = max(0, round(base − deduction)); "
            "base = 100 × passed_checks ÷ executed_checks; "
            "deduction = min(60, Σ open_findings × points[severity] × confidence_factor)"
        ),
        "severity_points": SEVERITY_POINTS,
        "confidence_factors": CONFIDENCE_FACTOR,
        "deduction_cap": DEDUCTION_CAP,
        "note": (
            "Security Posture is an evidence-based score derived from the "
            "security checks DevPilot was able to perform. It is not a "
            "percentage of 'how secure' the application is."
        ),
    }


def compute_security_posture(
    executed_rules: List[str],
    findings: List[Dict[str, Any]],
    statuses: Dict[str, Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Compute posture from executed checks and open findings."""
    if not executed_rules:
        return None

    open_by_rule: Dict[str, int] = {}
    deduction_raw = 0.0
    open_count = 0
    closed_count = 0

    for f in findings:
        status_entry = statuses.get(f["fingerprint"])
        status = (status_entry or {}).get("status", "open")
        if status in CLOSED_STATUSES:
            closed_count += 1
            continue  # excluded from deductions; still listed with its status
        open_count += 1
        rule_id = f.get("rule_id", "")
        # ENV-COMMITTED is tree-level, not tied to a per-file rule execution;
        # count it as its own check only when present.
        key = rule_id or "AD-HOC"
        open_by_rule[key] = open_by_rule.get(key, 0) + 1
        deduction_raw += SEVERITY_POINTS.get(f.get("severity", ""), 2) * \
            CONFIDENCE_FACTOR.get(f.get("confidence", ""), 0.25)

    executed_set = set(executed_rules)
    failed_rules = set(open_by_rule.keys())
    passed = len([r for r in executed_set if r not in failed_rules])
    total_checks = len(executed_set | failed_rules)

    base = 100.0 * passed / total_checks if total_checks else 0.0
    deduction = min(DEDUCTION_CAP, deduction_raw)
    score = max(0, round(base - deduction))

    by_sev_open = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for f in findings:
        entry = statuses.get(f["fingerprint"]) or {}
        if entry.get("status", "open") in CLOSED_STATUSES:
            continue
        sev = f.get("severity")
        if sev in by_sev_open:
            by_sev_open[sev] += 1

    return {
        "score": score,
        "executed_checks": total_checks,
        "passed_checks": passed,
        "failed_checks": len(failed_rules),
        "open_findings": open_count,
        "closed_findings": closed_count,
        "raw_deduction": round(deduction_raw, 1),
        "applied_deduction": round(deduction, 1),
        "open_by_severity": by_sev_open,
        **posture_formula(),
    }
