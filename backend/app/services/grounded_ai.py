"""Grounded AI: Ask-DevPilot retrieval pipeline + hallucination guards.

Workflow (Module 2 spec §18):

    Question → Repository Search → Relevant Code → Relevant Findings
      → Architecture Context → Groq → Evidence-Based Answer

Guarantees:
- Only retrieved repository data is placed in the model context; whole-repo
  dumps are never sent.
- The system prompt REQUIRES the refusal phrase
  "Insufficient evidence to answer confidently." when support is missing.
- After generation, every `file:line` citation in the answer is validated
  against the files actually present in the provided context; untraceable
  references are stripped from ``sources``.
- As a defense-in-depth measure, any raw-looking secret pattern in the answer
  is masked before it leaves this module.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple

from app.services.ai import _call_llm, _get_api_config
from app.services.secrets_detector import mask_secret

INSUFFICIENT_EVIDENCE = "Insufficient evidence to answer confidently."

ASK_SYSTEM_PROMPT = """You are DevPilot, a codebase analysis assistant.

You will receive CONTEXT built exclusively from real repository data:
code entities and relationships, static-analysis findings, dependency scan
results, architecture hotspots, and repository statistics.

ABSOLUTE RULES:
1. Use ONLY facts present in the CONTEXT. Never invent files, functions,
   classes, metrics, vulnerabilities, dependencies or measurements.
2. If the context does not contain enough evidence, reply EXACTLY:
   "{refusal}"
   You may add one short sentence listing what data would be needed.
3. Cite evidence inline using file_path:line format from the context only.
4. Static-analysis findings must be described as findings/evidence, never as
   confirmed exploitable vulnerabilities.
5. Performance topics: no timing measurements exist. Speak in terms of
   detected patterns only.
6. Be concise. Prefer bullet points. End with a "Sources:" list of the
   file paths you used.

CONTEXT:
{context}"""


# ── Retrieval ────────────────────────────────────────────────────────

def _keywords(question: str) -> List[str]:
    stop = {"what", "where", "why", "how", "which", "who", "the", "a", "an",
            "is", "are", "in", "on", "of", "to", "for", "and", "or", "does",
            "do", "my", "me", "should", "i", "it", "this", "that", "with",
            "most", "biggest", "first"}
    words = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]{2,}", question)
    return [w.lower() for w in words if w.lower() not in stop]


def _score_entity(text: str, kws: List[str]) -> int:
    t = text.lower()
    return sum(2 if kw in t else 0 for kw in kws) // 2


def select_relevant_nodes(
    question: str,
    nodes: List[Dict[str, Any]],
    limit: int = 25,
) -> List[Dict[str, Any]]:
    kws = _keywords(question)
    scored = []
    for n in nodes:
        blob = f"{n.get('name', '')} {n.get('file_path', '')} {n.get('label', '')}"
        s = _score_entity(blob, kws)
        if s > 0:
            scored.append((s, n))
    scored.sort(key=lambda x: (-x[0], str(x[1].get("file_path", ""))))
    return [n for _, n in scored[:limit]]


def select_relevant_findings(
    question: str,
    findings: List[Dict[str, Any]],
    limit: int = 15,
) -> List[Dict[str, Any]]:
    """Findings matching keywords; falls back to highest-severity open ones."""
    kws = _keywords(question)
    scored = []
    for f in findings:
        blob = " ".join(str(f.get(k, "")) for k in
                        ("title", "problem", "category", "category_label",
                         "rule_id", "file"))
        s = _score_entity(blob, kws)
        open_status = f.get("status", "open") == "open"
        if s > 0 and open_status:
            scored.append((s, f))
    scored.sort(key=lambda x: -x[0])
    if scored:
        return [f for _, f in scored[:limit]]
    order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    open_f = [f for f in findings if f.get("status", "open") == "open"]
    open_f.sort(key=lambda f: order.get(f.get("severity", ""), 9))
    return open_f[:limit]


def _format_entities(nodes: List[Dict[str, Any]], rels: List[Dict[str, Any]]) -> List[str]:
    lines = []
    node_ids = {n.get("node_id") for n in nodes}
    for n in nodes:
        fp = n.get("file_path") or ""
        span = f" lines {n['start_line']}-{n['end_line']}" if n.get("start_line") else ""
        lines.append(f"- [{n.get('label', '?')}] {n.get('name', '?')} ({fp}{span})")
    rel_lines = [r for r in rels
                 if r.get("from_id") in node_ids or r.get("to_id") in node_ids]
    for r in rel_lines[:40]:
        lines.append(f"  {r.get('from_name')} --[{r.get('type')}]--> {r.get('to_name')}")
    return lines


def build_grounded_context(
    question: str,
    nodes: List[Dict[str, Any]],
    rels: List[Dict[str, Any]],
    security_report: Optional[Dict[str, Any]],
    intel_report: Optional[Dict[str, Any]],
    riskmap: Optional[Dict[str, Any]],
    max_chars: int = 30_000,
) -> Tuple[str, Set[str]]:
    """Assemble the evidence context. Returns (context_text, context_file_set)."""
    parts: List[str] = []
    context_files: Set[str] = set()

    relevant_nodes = select_relevant_nodes(question, nodes)
    if nodes and not relevant_nodes:
        relevant_nodes = nodes[:20]

    # Findings first — they are the strongest actionable evidence.
    findings: List[Dict[str, Any]] = []
    deps_section: List[str] = []
    stats_section: List[str] = []

    if security_report:
        findings = select_relevant_findings(
            question, security_report.get("findings", []))
        counts = security_report.get("counts", {})
        posture = security_report.get("posture") or {}
        parts.append(f"SECURITY POSTURE: {posture.get('score', 'Not analyzed')}/100 "
                     f"(evidence-based; executed checks: {posture.get('executed_checks', 0)})")
        parts.append(f"FINDING COUNTS: {counts}")

    if intel_report:
        st = intel_report.get("stats", {})
        stats_section = [
            f"- files analyzed: {st.get('analyzed_files')} / {st.get('filtered_files')} filtered",
            f"- lines of code: {st.get('lines_of_code')}",
            f"- languages: {st.get('language_count')} ({', '.join(list((st.get('languages') or {}).keys())[:6])})",
            f"- functions: {st.get('functions')}, classes: {st.get('classes')}",
            f"- test files: {st.get('test_files')} vs source files {st.get('source_files')}",
            f"- external dependencies: {st.get('external_dependencies')} "
            f"(lockfile: {'yes' if st.get('has_lockfile') else 'no'})",
        ]
        health = intel_report.get("health") or {}
        stats_section.append(f"- code health overall: {health.get('overall')}")
        stats_section.append(f"- avg complexity proxy: {st.get('avg_complexity')}")

    if riskmap and riskmap.get("has_graph"):
        hotspots = (riskmap.get("hotspots") or [])[:5]
        cycles = (riskmap.get("cycles") or [])[:3]
        parts.append("ARCHITECTURE HOTSPOTS:")
        for h in hotspots:
            parts.append(f"- {h.get('name')} ({h.get('file_path')}) "
                         f"risk={h.get('risk')} fan_in={h.get('metrics', {}).get('fan_in')}")
        for c in cycles:
            parts.append(f"- circular dependency: {' <-> '.join(c.get('files', [])[:5])}")
        for h in hotspots:
            fp = h.get("file_path")
            if fp:
                context_files.add(fp)

    if findings:
        parts.append("RELEVANT FINDINGS (static analysis):")
        for f in findings:
            sev = f.get("severity", "")
            conf = f.get("confidence", "")
            title = f.get("title") or f.get("problem", "")
            parts.append(f"- [{sev}/{conf}] {title} — {f.get('file')}:{f.get('line')}"
                         + (f" in {f['symbol']}" if f.get("symbol") else ""))
            why = f.get("why") or f.get("explanation") or ""
            if why:
                parts.append(f"    why: {why[:220]}")
            context_files.add(f.get("file", ""))

    if relevant_nodes:
        parts.append("RELEVANT CODE ENTITIES:")
        parts.extend(_format_entities(relevant_nodes, rels))
        for n in relevant_nodes:
            fp = n.get("file_path") or n.get("path")
            if fp:
                context_files.add(fp)

    if stats_section:
        parts.append("REPOSITORY STATISTICS:")
        parts.extend(stats_section)

    if deps_section:
        parts.append("DEPENDENCIES:")
        parts.extend(deps_section)

    if security_report and not security_report.get("findings"):
        parts.append("NOTE: No security deep-scan report exists yet for this repository.")

    context = "\n".join(parts)
    if len(context) > max_chars:
        context = context[:max_chars] + "\n[context truncated]"
    return context, context_files


# ── Post-generation validation ───────────────────────────────────────

_CITATION_RE = re.compile(r"([\w./\\-]+\.[A-Za-z0-9]{1,10})(?::(\d+))?")
_SECRETISH_RE = re.compile(
    r"\b(AKIA[0-9A-Z]{12,}|gh[pousr]_[A-Za-z0-9]{20,}|xox[baprs]-[A-Za-z0-9-]{10,}|"
    r"AIza[0-9A-Za-z_-]{30,}|sk-[A-Za-z0-9_-]{28,}|eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9._-]+)"
)


def validate_answer(answer: str, context_files: Set[str]) -> Dict[str, Any]:
    """Strip untraceable citations; mask secret-like strings defensively."""
    cleaned = answer

    def _mask(m: "re.Match[str]") -> str:
        return mask_secret(m.group(0))

    if _SECRETISH_RE.search(cleaned):
        cleaned = _SECRETISH_RE.sub(_mask, cleaned)

    sources: List[Dict[str, Any]] = []
    dropped: List[str] = []
    seen: Set[str] = set()
    for m in _CITATION_RE.finditer(cleaned):
        path = m.group(1).replace("\\", "/")
        norm = path.lstrip("./")
        matched = norm in context_files or any(cf.endswith(norm) for cf in context_files) \
            or any(norm.endswith(cf) for cf in context_files)
        key = f"{norm}:{m.group(2) or ''}"
        if key in seen:
            continue
        seen.add(key)
        if matched:
            sources.append({"file": norm, "line": m.group(2) or "", "traced": True})
        else:
            dropped.append(norm)
    return {"answer": cleaned, "sources": sources, "dropped_citations": dropped}


def insufficient_evidence_answer() -> Dict[str, Any]:
    return {
        "answer": INSUFFICIENT_EVIDENCE,
        "sources": [],
        "evidence_used": False,
        "error": None,
    }


# ── Public entry point ───────────────────────────────────────────────

async def ask_devpilot(
    question: str,
    nodes: List[Dict[str, Any]],
    rels: List[Dict[str, Any]],
    security_report: Optional[Dict[str, Any]],
    intel_report: Optional[Dict[str, Any]],
    riskmap: Optional[Dict[str, Any]],
    owner: str,
    repo: str,
) -> Dict[str, Any]:
    context, context_files = build_grounded_context(
        question, nodes, rels, security_report, intel_report, riskmap)

    has_evidence = bool(context_files) or bool(security_report) or bool(intel_report)
    config = _get_api_config()

    if not config:
        return {
            "answer": (
                "AI is not configured on this server (GROQ_API_KEY missing), so no "
                "generated explanation is available. The underlying analysis data "
                "(scores, findings, statistics) is computed deterministically and "
                "remains available throughout the app."
                + ("" if has_evidence else f" {INSUFFICIENT_EVIDENCE}")
            ),
            "sources": [],
            "evidence_used": False,
            "error": "LLM not configured",
        }

    if not has_evidence:
        return insufficient_evidence_answer()

    messages = [{
        "role": "system",
        "content": ASK_SYSTEM_PROMPT.format(context=context, refusal=INSUFFICIENT_EVIDENCE),
    }, {
        "role": "user",
        "content": question,
    }]

    try:
        raw = await _call_llm(messages, temperature=0.2)
    except Exception as exc:
        return {
            "answer": f"The AI provider could not be reached ({exc.__class__.__name__}). "
                      f"No answer was generated.",
            "sources": [],
            "evidence_used": False,
            "error": "LLM request failed",
        }

    validated = validate_answer(raw, context_files)
    low_evidence = len(validated["sources"]) == 0 and not context_files
    return {
        "answer": validated["answer"],
        "sources": validated["sources"],
        "dropped_citations": validated["dropped_citations"],
        "evidence_used": len(validated["sources"]) > 0 or bool(context_files),
        "low_confidence": low_evidence,
        "error": None,
    }


# ── Deterministic insights ───────────────────────────────────────────

def build_insights(
    intel_report: Optional[Dict[str, Any]],
    security_report: Optional[Dict[str, Any]],
    riskmap: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Evidence-backed insights assembled deterministically (no AI).

    Each insight carries explicit evidence pointers so the UI can link to the
    real artifacts behind it.
    """
    insights: List[Dict[str, Any]] = []

    if security_report:
        counts = security_report.get("counts", {})
        sec = counts.get("security", {})
        crit, high = sec.get("CRITICAL", 0), sec.get("HIGH", 0)
        secrets_n = counts.get("secrets", 0)

        if secrets_n:
            insights.append({
                "id": "ins-secrets",
                "kind": "security",
                "tone": "critical",
                "title": f"{secrets_n} hardcoded secret(s) detected",
                "detail": "Masked previews are shown; rotate exposed credentials immediately.",
                "evidence": [
                    {"label": s.get("masked_preview"), "file": s.get("file"),
                     "line": s.get("line")}
                    for s in (security_report.get("secrets") or [])[:3]
                ],
                "href": "/security",
            })
        if crit + high:
            insights.append({
                "id": "ins-security-findings",
                "kind": "security",
                "tone": "warning",
                "title": f"{crit + high} critical/high security finding(s)",
                "detail": "Static-analysis detections with strong or medium confidence.",
                "evidence": [
                    {"label": f.get("title"), "file": f.get("file"), "line": f.get("line")}
                    for f in security_report.get("findings", [])
                    if f.get("severity") in ("CRITICAL", "HIGH")
                    and f.get("status", "open") == "open"
                ][:3],
                "href": "/security",
            })
        dep_vulns = ((security_report.get("dependencies") or {}).get("vulnerabilities")) or []
        if dep_vulns:
            insights.append({
                "id": "ins-deps",
                "kind": "dependency",
                "tone": "warning",
                "title": f"{len(dep_vulns)} known vulnerability/vulnerabilities in pinned dependencies",
                "detail": "Matched live against OSV.dev using manifest versions.",
                "evidence": [
                    {"label": f"{v['package']} {v.get('vulnerability_id')}",
                     "file": v.get("manifest_source")}
                    for v in dep_vulns[:3]
                ],
                "href": "/security",
            })

    if security_report:
        perf = security_report.get("performance_issues") or []
        o_n = [p for p in perf if p.get("rule_id") in ("PERF-NESTED-LOOPS", "PERF-LINEAR-SEARCH-IN-LOOP")]
        if o_n:
            insights.append({
                "id": "ins-perf",
                "kind": "performance",
                "tone": "info",
                "title": f"{len(o_n)} potential O(n²)+ pattern(s) (static detection)",
                "detail": "Nested loops / linear searches inside loops. No measured timings exist.",
                "evidence": [
                    {"label": p.get("title"), "file": p.get("file"), "line": p.get("line")}
                    for p in o_n[:3]
                ],
                "href": "/intelligence",
            })

    if intel_report:
        st = intel_report.get("stats", {})
        src, tests = st.get("source_files", 0), st.get("test_files", 0)
        if (src + tests) > 4 and tests / max(1, src + tests) < 0.10:
            insights.append({
                "id": "ins-tests",
                "kind": "testing",
                "tone": "info",
                "title": "Very few test files relative to source code",
                "detail": f"{tests} test file(s) vs {src} source file(s) — regression safety net is thin.",
                "evidence": [{"label": "repository statistics"}],
                "href": "/intelligence",
            })
        if st.get("has_lockfile"):
            insights.append({
                "id": "ins-lockfile-good",
                "kind": "good-practice",
                "tone": "good",
                "title": "Lockfile present — dependency versions are pinned",
                "detail": "Reproducible builds and reliable vulnerability matching are possible.",
                "evidence": [{"label": "repository statistics"}],
                "href": "/security",
            })

    if riskmap and riskmap.get("has_graph"):
        hotspots = riskmap.get("hotspots") or []
        if hotspots:
            top = hotspots[0]
            insights.append({
                "id": "ins-hotspot",
                "kind": "architecture",
                "tone": "info",
                "title": f"Architecture hotspot: {top.get('name')}",
                "detail": f"fan-in {top.get('metrics', {}).get('fan_in')} · "
                          f"fan-out {top.get('metrics', {}).get('fan_out')} · "
                          f"risk {top.get('risk')}. Changes here affect many dependents.",
                "evidence": [{"label": top.get("file_path"), "file": top.get("file_path"),
                              "line": None}],
                "href": "/architecture",
            })

    if not insights:
        insights.append({
            "id": "ins-none",
            "kind": "info",
            "tone": "neutral",
            "title": "No analysis data available yet",
            "detail": "Run an analysis and a security deep scan to generate evidence-backed insights.",
            "evidence": [],
            "href": "/command-center",
        })

    return insights[:8]
