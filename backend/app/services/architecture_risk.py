"""Architecture Risk Map.

Derives architectural hotspots from the existing dependency graph
(nodes + relationships produced by the standard DevPilot graph build):

- highly connected modules (total degree)
- frequently referenced modules (fan-in) -> potential single points of failure
- large/complex classes (span from node metadata)
- circular dependencies (Tarjan strongly-connected components)
- deep dependency chains (longest path estimate, bounded)

Reuses graph.py accessors — no separate graph system is created.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Set, Tuple

from app.services.graph import get_all_nodes, get_all_relationships


def _build_adjacency(rels: List[Dict[str, Any]]) -> Tuple[Dict[str, Set[str]], Dict[str, Set[str]]]:
    out: Dict[str, Set[str]] = defaultdict(set)
    inc: Dict[str, Set[str]] = defaultdict(set)
    for r in rels:
        f, t = r.get("from_id"), r.get("to_id")
        if not f or not t or f == t:
            continue
        out[f].add(t)
        inc[t].add(f)
    return out, inc


def _tarjan_scc(nodes: List[str], adj: Dict[str, Set[str]]) -> List[List[str]]:
    index_counter = [0]
    stack: List[str] = []
    on_stack: Set[str] = set()
    index: Dict[str, int] = {}
    lowlink: Dict[str, int] = {}
    result: List[List[str]] = []

    def strongconnect(v: str) -> None:
        # iterative Tarjan to avoid recursion limits
        work = [(v, iter(adj.get(v, ())))]
        index[v] = lowlink[v] = index_counter[0]
        index_counter[0] += 1
        stack.append(v)
        on_stack.add(v)

        while work:
            node, it = work[-1]
            advanced = False
            for w in it:
                if w not in index:
                    index[w] = lowlink[w] = index_counter[0]
                    index_counter[0] += 1
                    stack.append(w)
                    on_stack.add(w)
                    work.append((w, iter(adj.get(w, ()))))
                    advanced = True
                    break
                elif w in on_stack:
                    lowlink[node] = min(lowlink[node], index[w])
            if advanced:
                continue
            work.pop()
            if work:
                parent = work[-1][0]
                lowlink[parent] = min(lowlink[parent], lowlink[node])
            if lowlink[node] == index[node]:
                scc: List[str] = []
                while True:
                    w = stack.pop()
                    on_stack.discard(w)
                    scc.append(w)
                    if w == node:
                        break
                result.append(scc)

    for v in nodes:
        if v not in index:
            strongconnect(v)
    return result


def _longest_path_estimate(start: str, adj: Dict[str, Set[str]], max_depth: int = 12) -> int:
    best = 0
    stack: List[Tuple[str, int, Set[str]]] = [(start, 0, {start})]
    while stack and best < max_depth:
        node, depth, seen = stack.pop()
        best = max(best, depth)
        for nxt in adj.get(node, ()):
            if nxt not in seen and depth + 1 <= max_depth:
                stack.append((nxt, depth + 1, seen | {nxt}))
    return best


def compute_architecture_risk(rid: str) -> Dict[str, Any]:
    raw_nodes = get_all_nodes(rid)
    nodes: List[Dict[str, Any]] = raw_nodes
    rels = get_all_relationships(rid)

    if not nodes:
        return {"has_graph": False, "hotspots": [], "cycles": [], "summary": {}}

    node_by_id = {n.get("node_id"): n for n in nodes}
    out_adj, in_adj = _build_adjacency(rels)

    hotspots: List[Dict[str, Any]] = []
    scored: List[Tuple[float, str, Dict[str, Any]]] = []

    for n in nodes:
        nid = n.get("node_id", "")
        fan_in = len(in_adj.get(nid, ()))
        fan_out = len(out_adj.get(nid, ()))
        total = fan_in + fan_out
        span = 0
        try:
            s = int(n.get("start_line") or 0)
            e = int(n.get("end_line") or 0)
            span = max(0, e - s)
        except Exception:
            span = 0

        score = 0.0
        reasons: List[str] = []
        if total >= 8:
            reasons.append(f"Highly connected: {total} relationships ({fan_in} incoming / {fan_out} outgoing)")
            score += total * 2.5
        elif total >= 5:
            reasons.append(f"Well connected: {total} relationships ({fan_in} in / {fan_out} out)")
            score += total * 1.2
        if fan_in >= 6:
            reasons.append(f"Frequently referenced ({fan_in} dependents) — potential single point of failure")
            score += fan_in * 3
        if span > 250:
            reasons.append(f"Large {str(n.get('label') or 'entity').lower()} (~{span} lines)")
            score += 18
        chain = _longest_path_estimate(nid, out_adj)
        if chain >= 6:
            reasons.append(f"Deep dependency chain from here (~{chain} hops)")
            score += chain * 2

        if reasons:
            risk = "high" if score >= 40 else ("medium" if score >= 20 else "low")
            hotspots.append({
                "node_id": nid,
                "name": n.get("name", ""),
                "label": n.get("label", ""),
                "file_path": n.get("file_path") or "",
                "risk": risk,
                "score": round(score, 1),
                "metrics": {"fan_in": fan_in, "fan_out": fan_out, "total_degree": total, "span_lines": span},
                "reasons": reasons,
            })

    hotspots.sort(key=lambda h: (-h["score"], -h["metrics"]["total_degree"]))
    hotspots = hotspots[:25]

    # circular dependencies at module/file granularity
    file_adj: Dict[str, Set[str]] = defaultdict(set)
    for rel in rels:
        f = node_by_id.get(rel.get("from_id"), {})
        t = node_by_id.get(rel.get("to_id"), {})
        fp_f = (f.get("file_path") or "").split("/")[-1] if f else ""
        fp_t = (t.get("file_path") or "").split("/")[-1] if t else ""
        if fp_f and fp_t and fp_f != fp_t:
            file_adj[f"{fp_f}|{(f.get('file_path') or '')}"].add(f"{fp_t}|{(t.get('file_path') or '')}")

    files = list(file_adj.keys())
    sccs = _tarjan_scc(files, file_adj)
    cycles = []
    for scc in sccs:
        if len(scc) > 1:
            display = sorted({p.split("|")[0] for p in scc})
            cycles.append({"files": display[:8], "size": len(scc)})
    cycles.sort(key=lambda c: -c["size"])
    cycles = cycles[:10]

    summary = {
        "nodes": len(nodes),
        "relationships": len(rels),
        "high_risk": sum(1 for h in hotspots if h["risk"] == "high"),
        "medium_risk": sum(1 for h in hotspots if h["risk"] == "medium"),
        "circular_dependency_groups": len(cycles),
    }

    return {
        "has_graph": True,
        "hotspots": hotspots,
        "cycles": [{"files": c["files"], "size": c["size"]} for c in cycles],
        "summary": summary,
        "methodology": "Graph-derived metrics (degree centrality, fan-in concentration, entity size, SCC cycle detection). Static structural analysis.",
    }
