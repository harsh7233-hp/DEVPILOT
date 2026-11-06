"""Priority queue computation.

Deterministic ordering — no arbitrary ranking, no AI involvement:

    priority_score = severity_weight[severity]
                     × confidence_factor[confidence]
                     × (1 + min(dependents, 20) / 20 × 0.5)

    severity_weight : CRITICAL 100 · HIGH 70 · MEDIUM 40 · LOW 15
    confidence_factor: HIGH 1.0 · MEDIUM 0.75 · LOW 0.45
    dependents      : fan-in of the file's node in the dependency graph when
                      available (impact proxy), else 0

Buckets derived from the score:
    ≥ 65 Critical · ≥ 42 High · ≥ 22 Medium · else Low

Ties break deterministically on (severity, confidence, file, line).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

SEVERITY_WEIGHT = {"CRITICAL": 100, "HIGH": 70, "MEDIUM": 40, "LOW": 15}
CONFIDENCE_FACTOR = {"HIGH": 1.0, "MEDIUM": 0.75, "LOW": 0.45}
_SEV_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
_CONF_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}


def bucket_for(score: float) -> str:
    if score >= 65:
        return "Critical"
    if score >= 42:
        return "High"
    if score >= 22:
        return "Medium"
    return "Low"


def compute_priority(
    findings: List[Dict[str, Any]],
    dependents_by_file: Optional[Dict[str, int]] = None,
) -> List[Dict[str, Any]]:
    dependents_by_file = dependents_by_file or {}
    items: List[Dict[str, Any]] = []
    for f in findings:
        sev_w = SEVERITY_WEIGHT.get(f.get("severity", ""), 10)
        conf_f = CONFIDENCE_FACTOR.get(f.get("confidence", ""), 0.45)
        deps = dependents_by_file.get(f.get("file", ""), 0)
        impact_mult = 1 + min(deps, 20) / 20 * 0.5
        score = round(sev_w * conf_f * impact_mult, 1)
        items.append({
            "fingerprint": f["fingerprint"],
            "kind": f.get("category_label") or f.get("category") or "finding",
            "title": f.get("title") or f.get("problem", ""),
            "severity": f.get("severity"),
            "confidence": f.get("confidence"),
            "priority_score": score,
            "bucket": bucket_for(score),
            "dependents": deps,
            "status": f.get("status", "open"),
            "target": {
                "file": f.get("file"),
                "line": f.get("line"),
                "symbol": f.get("symbol"),
            },
            "sort_key": (-score,
                         _SEV_ORDER.get(f.get("severity"), 9),
                         _CONF_ORDER.get(f.get("confidence"), 9),
                         f.get("file", ""),
                         f.get("line", 0)),
        })
    items.sort(key=lambda x: x["sort_key"])
    for it in items:
        it.pop("sort_key", None)
    return items
