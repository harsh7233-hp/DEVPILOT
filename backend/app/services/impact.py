from __future__ import annotations

from collections import deque
from typing import Any, Dict, List, Optional, Set, Tuple


# ── Data types ─────────────────────────────────────────────────────


class ImpactNode:
    __slots__ = ("node_id", "label", "name", "properties")

    def __init__(self, node_id: str, label: str, name: str, properties: Optional[Dict[str, Any]] = None) -> None:
        self.node_id = node_id
        self.label = label
        self.name = name
        self.properties = properties or {}

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"node_id": self.node_id, "label": self.label, "name": self.name}
        d.update(self.properties)
        return d


class AffectedNode:
    __slots__ = ("node", "depth", "path")

    def __init__(self, node: ImpactNode, depth: int, path: List[str]) -> None:
        self.node = node
        self.depth = depth
        self.path = path

    def to_dict(self) -> Dict[str, Any]:
        return {"node": self.node.to_dict(), "depth": self.depth, "path": self.path}


class ImpactResult:
    def __init__(self) -> None:
        self.target: Optional[ImpactNode] = None
        self.direct_impact: List[AffectedNode] = []
        self.indirect_impact: List[AffectedNode] = []
        self.dependency_paths: List[List[str]] = []
        self.metrics: Dict[str, Any] = {}
        self.risk: Dict[str, Any] = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target": self.target.to_dict() if self.target else None,
            "risk": self.risk,
            "metrics": self.metrics,
            "direct_impact": [a.to_dict() for a in self.direct_impact],
            "indirect_impact": [a.to_dict() for a in self.indirect_impact],
            "dependency_paths": self.dependency_paths,
        }


# ── In-memory graph representation ────────────────────────────────


class Graph:
    def __init__(
        self,
        nodes: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]],
    ) -> None:
        self._nodes: Dict[str, ImpactNode] = {}
        self._outgoing: Dict[str, List[Tuple[str, str]]] = {}
        self._incoming: Dict[str, List[Tuple[str, str]]] = {}

        for n in nodes:
            nid = n.get("node_id", "")
            label = n.get("label", "")
            name = n.get("name", "")
            props = {k: v for k, v in n.items() if k not in ("node_id", "label", "name", "repo_id")}
            self._nodes[nid] = ImpactNode(nid, label, name, props)
            self._outgoing.setdefault(nid, [])
            self._incoming.setdefault(nid, [])

        for r in relationships:
            src = r.get("from_id", "")
            tgt = r.get("to_id", "")
            rel_type = r.get("type", "")
            if src in self._nodes and tgt in self._nodes:
                self._outgoing.setdefault(src, []).append((tgt, rel_type))
                self._incoming.setdefault(tgt, []).append((src, rel_type))

    def get_node(self, node_id: str) -> Optional[ImpactNode]:
        return self._nodes.get(node_id)

    def get_incoming(self, node_id: str) -> List[Tuple[str, str]]:
        return self._incoming.get(node_id, [])

    def get_outgoing(self, node_id: str) -> List[Tuple[str, str]]:
        return self._outgoing.get(node_id, [])

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        return sum(len(v) for v in self._outgoing.values())


# ── Impact analysis ────────────────────────────────────────────────


def analyze_impact(
    graph: Graph,
    target_node_id: str,
    max_depth: int = 20,
) -> ImpactResult:
    result = ImpactResult()

    target = graph.get_node(target_node_id)
    if target is None:
        result.metrics = {"error": "Target node not found"}
        result.risk = {"level": "unknown", "score": 0, "reason": "Target node not found in graph"}
        return result

    result.target = target

    visited: Set[str] = {target_node_id}
    direct: List[AffectedNode] = []
    indirect: List[AffectedNode] = []
    all_paths: List[List[str]] = []

    queue: deque[Tuple[str, List[str], int]] = deque()
    queue.append((target_node_id, [target_node_id], 0))

    while queue:
        current_id, path, depth = queue.popleft()

        if depth >= max_depth:
            continue

        for dep_id, rel_type in graph.get_incoming(current_id):
            if dep_id in visited:
                continue

            visited.add(dep_id)
            dep_node = graph.get_node(dep_id)
            if dep_node is None:
                continue

            new_path = path + [dep_id]
            affected = AffectedNode(dep_node, depth + 1, new_path)

            if depth + 1 == 1:
                direct.append(affected)
            else:
                indirect.append(affected)

            all_paths.append(new_path)
            queue.append((dep_id, new_path, depth + 1))

    result.direct_impact = direct
    result.indirect_impact = indirect
    result.dependency_paths = all_paths
    result.metrics = _compute_metrics(target, direct, indirect, graph)
    result.risk = _compute_risk(result.metrics)
    return result


# ── Metrics ────────────────────────────────────────────────────────


def _compute_metrics(
    target: ImpactNode,
    direct: List[AffectedNode],
    indirect: List[AffectedNode],
    graph: Graph,
) -> Dict[str, Any]:
    all_affected = direct + indirect

    affected_files: Set[str] = set()
    affected_functions: Set[str] = set()
    affected_classes: Set[str] = set()
    affected_modules: Set[str] = set()
    affected_apis: Set[str] = set()

    for a in all_affected:
        n = a.node
        if n.label == "File":
            affected_files.add(n.node_id)
        elif n.label == "Function":
            affected_functions.add(n.node_id)
        elif n.label == "Class":
            affected_classes.add(n.node_id)
        elif n.label == "ApiRoute":
            affected_apis.add(n.node_id)
        elif n.label == "Method":
            affected_functions.add(n.node_id)

        file_path = n.properties.get("file_path") or n.properties.get("path")
        if file_path:
            affected_modules.add(file_path)

    max_depth = 0
    for a in all_affected:
        if a.depth > max_depth:
            max_depth = a.depth

    return {
        "affected_files": len(affected_files),
        "affected_functions": len(affected_functions),
        "affected_classes": len(affected_classes),
        "affected_modules": len(affected_modules),
        "affected_apis": len(affected_apis),
        "direct_dependencies": len(direct),
        "indirect_dependencies": len(indirect),
        "dependency_depth": max_depth,
        "total_affected": len(all_affected),
    }


# ── Risk scoring ───────────────────────────────────────────────────
#
# Deterministic, explainable risk scoring.
#
# Base score starts at 0. Additions:
#
#   +1 per direct dependency        (breadth)
#   +2 per indirect dependency      (breadth of cascade)
#   +3 per depth level              (depth of cascade)
#   +5 if any API route affected    (public surface area)
#   +3 if any class affected        (OOP coupling)
#
# Thresholds:
#   0-8   → LOW     Few dependencies, shallow cascade
#   9-20  → MEDIUM  Moderate dependencies or depth
#   21+   → HIGH    Large cascade or critical involvement
#
# This is transparent and deterministic.


def _compute_risk(metrics: Dict[str, Any]) -> Dict[str, Any]:
    score = 0
    reasons: List[str] = []

    direct = metrics.get("direct_dependencies", 0)
    indirect = metrics.get("indirect_dependencies", 0)
    depth = metrics.get("dependency_depth", 0)
    apis = metrics.get("affected_apis", 0)
    classes = metrics.get("affected_classes", 0)
    files = metrics.get("affected_files", 0)
    total = metrics.get("total_affected", 0)

    score += direct * 1
    if direct > 0:
        reasons.append(f"{direct} direct dependents")

    score += indirect * 2
    if indirect > 0:
        reasons.append(f"{indirect} indirect dependents")

    score += depth * 3
    if depth > 0:
        reasons.append(f"dependency depth of {depth}")

    if apis > 0:
        score += 5
        reasons.append(f"{apis} API route(s) affected")

    if classes > 0:
        score += 3
        reasons.append(f"{classes} class(es) affected")

    if score <= 8:
        level = "low"
        color = "#22c55e"
    elif score <= 20:
        level = "medium"
        color = "#f59e0b"
    else:
        level = "high"
        color = "#ef4444"

    summary = f"Risk is {level.upper()} — {total} component(s) affected."
    if reasons:
        summary += " " + "; ".join(reasons) + "."

    return {
        "level": level,
        "score": score,
        "color": color,
        "reasons": reasons,
        "summary": summary,
        "formula": "score = (direct × 1) + (indirect × 2) + (depth × 3) + (apis × 5) + (classes × 3)",
    }
