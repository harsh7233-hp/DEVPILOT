from __future__ import annotations

from typing import Any, Dict, List

import pytest

from app.services.impact import (
    AffectedNode,
    Graph,
    ImpactNode,
    ImpactResult,
    _compute_metrics,
    _compute_risk,
    analyze_impact,
)


# ── Helpers ────────────────────────────────────────────────────────


def _make_nodes(*ids: str, label: str = "Function") -> List[Dict[str, Any]]:
    return [{"node_id": nid, "label": label, "name": nid} for nid in ids]


def _make_rels(*triples: tuple) -> List[Dict[str, Any]]:
    return [{"from_id": s, "to_id": t, "type": r} for s, r, t in triples]


def _node(nid: str, label: str = "Function", name: str = "") -> Dict[str, Any]:
    return {"node_id": nid, "label": label, "name": name or nid}


# ── Graph construction ────────────────────────────────────────────


class TestGraphConstruction:
    def test_empty_graph(self):
        g = Graph([], [])
        assert g.node_count == 0
        assert g.edge_count == 0

    def test_nodes_only(self):
        g = Graph(_make_nodes("a", "b", "c"), [])
        assert g.node_count == 3
        assert g.edge_count == 0

    def test_edges_only(self):
        rels = _make_rels(("a", "IMPORTS", "b"))
        g = Graph([], rels)
        assert g.node_count == 0
        assert g.edge_count == 0

    def test_full_graph(self):
        nodes = _make_nodes("a", "b", "c")
        rels = _make_rels(("a", "IMPORTS", "b"), ("b", "CALLS", "c"))
        g = Graph(nodes, rels)
        assert g.node_count == 3
        assert g.edge_count == 2

    def test_get_node(self):
        g = Graph(_make_nodes("a", "b"), [])
        n = g.get_node("a")
        assert n is not None
        assert n.node_id == "a"
        assert g.get_node("z") is None

    def test_get_incoming(self):
        nodes = _make_nodes("a", "b")
        rels = _make_rels(("a", "IMPORTS", "b"))
        g = Graph(nodes, rels)
        incoming = g.get_incoming("b")
        assert len(incoming) == 1
        assert incoming[0] == ("a", "IMPORTS")

    def test_get_outgoing(self):
        nodes = _make_nodes("a", "b")
        rels = _make_rels(("a", "IMPORTS", "b"))
        g = Graph(nodes, rels)
        outgoing = g.get_outgoing("a")
        assert len(outgoing) == 1
        assert outgoing[0] == ("b", "IMPORTS")

    def test_self_loop_excluded(self):
        nodes = _make_nodes("a")
        rels = _make_rels(("a", "CALLS", "a"))
        g = Graph(nodes, rels)
        result = analyze_impact(g, "a")
        assert len(result.direct_impact) == 0
        assert len(result.indirect_impact) == 0

    def test_duplicate_relationships(self):
        nodes = _make_nodes("a", "b")
        rels = _make_rels(("a", "IMPORTS", "b"), ("a", "CALLS", "b"))
        g = Graph(nodes, rels)
        incoming = g.get_incoming("b")
        assert len(incoming) == 2


# ── No dependencies ───────────────────────────────────────────────


class TestNoDependencies:
    def test_single_node(self):
        g = Graph(_make_nodes("a"), [])
        result = analyze_impact(g, "a")
        assert result.target is not None
        assert result.target.node_id == "a"
        assert len(result.direct_impact) == 0
        assert len(result.indirect_impact) == 0
        assert result.metrics["total_affected"] == 0
        assert result.risk["level"] == "low"
        assert result.risk["score"] == 0

    def test_two_unrelated_nodes(self):
        g = Graph(_make_nodes("a", "b"), [])
        result = analyze_impact(g, "a")
        assert len(result.direct_impact) == 0
        assert len(result.indirect_impact) == 0

    def test_target_not_found(self):
        g = Graph(_make_nodes("a"), [])
        result = analyze_impact(g, "nonexistent")
        assert result.target is None
        assert result.risk["level"] == "unknown"


# ── One direct dependency ─────────────────────────────────────────


class TestSingleDirectDependency:
    def test_one_incoming(self):
        nodes = _make_nodes("a", "b")
        rels = _make_rels(("a", "IMPORTS", "b"))
        g = Graph(nodes, rels)
        result = analyze_impact(g, "b")
        assert len(result.direct_impact) == 1
        assert len(result.indirect_impact) == 0
        assert result.direct_impact[0].node.node_id == "a"
        assert result.direct_impact[0].depth == 1

    def test_single_path(self):
        nodes = _make_nodes("a", "b")
        rels = _make_rels(("a", "IMPORTS", "b"))
        g = Graph(nodes, rels)
        result = analyze_impact(g, "b")
        assert len(result.dependency_paths) == 1
        assert result.dependency_paths[0] == ["b", "a"]

    def test_metrics(self):
        nodes = _make_nodes("a", "b")
        rels = _make_rels(("a", "IMPORTS", "b"))
        g = Graph(nodes, rels)
        result = analyze_impact(g, "b")
        assert result.metrics["direct_dependencies"] == 1
        assert result.metrics["indirect_dependencies"] == 0
        assert result.metrics["dependency_depth"] == 1
        assert result.metrics["total_affected"] == 1

    def test_risk_low(self):
        nodes = _make_nodes("a", "b")
        rels = _make_rels(("a", "IMPORTS", "b"))
        g = Graph(nodes, rels)
        result = analyze_impact(g, "b")
        assert result.risk["level"] == "low"
        assert result.risk["score"] == 4


# ── Multiple direct dependencies ──────────────────────────────────


class TestMultipleDirectDependencies:
    def test_two_incoming(self):
        nodes = _make_nodes("a", "b", "target")
        rels = _make_rels(("a", "IMPORTS", "target"), ("b", "CALLS", "target"))
        g = Graph(nodes, rels)
        result = analyze_impact(g, "target")
        assert len(result.direct_impact) == 2
        assert len(result.indirect_impact) == 0
        ids = {d.node.node_id for d in result.direct_impact}
        assert ids == {"a", "b"}

    def test_three_incoming(self):
        nodes = _make_nodes("a", "b", "c", "target")
        rels = _make_rels(
            ("a", "IMPORTS", "target"),
            ("b", "CALLS", "target"),
            ("c", "USES", "target"),
        )
        g = Graph(nodes, rels)
        result = analyze_impact(g, "target")
        assert len(result.direct_impact) == 3
        assert result.metrics["direct_dependencies"] == 3
        assert result.risk["score"] == 6


# ── Deep dependency chain ─────────────────────────────────────────


class TestDeepChain:
    def test_two_level_chain(self):
        nodes = _make_nodes("a", "b", "c")
        rels = _make_rels(("a", "IMPORTS", "b"), ("b", "IMPORTS", "c"))
        g = Graph(nodes, rels)
        result = analyze_impact(g, "c")
        assert len(result.direct_impact) == 1
        assert result.direct_impact[0].node.node_id == "b"
        assert result.direct_impact[0].depth == 1
        assert len(result.indirect_impact) == 1
        assert result.indirect_impact[0].node.node_id == "a"
        assert result.indirect_impact[0].depth == 2
        assert result.metrics["dependency_depth"] == 2
        assert result.metrics["total_affected"] == 2

    def test_four_level_chain(self):
        nodes = _make_nodes("a", "b", "c", "d")
        rels = _make_rels(
            ("a", "IMPORTS", "b"),
            ("b", "IMPORTS", "c"),
            ("c", "IMPORTS", "d"),
        )
        g = Graph(nodes, rels)
        result = analyze_impact(g, "d")
        assert len(result.direct_impact) == 1
        assert len(result.indirect_impact) == 2
        assert result.metrics["dependency_depth"] == 3
        depths = {a.depth for a in result.indirect_impact}
        assert depths == {2, 3}

    def test_chain_paths(self):
        nodes = _make_nodes("a", "b", "c")
        rels = _make_rels(("a", "IMPORTS", "b"), ("b", "IMPORTS", "c"))
        g = Graph(nodes, rels)
        result = analyze_impact(g, "c")
        assert len(result.dependency_paths) == 2
        assert ["c", "b"] in result.dependency_paths
        assert ["c", "b", "a"] in result.dependency_paths

    def test_chain_risk_medium(self):
        nodes = _make_nodes("a", "b", "c", "d")
        rels = _make_rels(
            ("a", "IMPORTS", "b"),
            ("b", "IMPORTS", "c"),
            ("c", "IMPORTS", "d"),
        )
        g = Graph(nodes, rels)
        result = analyze_impact(g, "d")
        assert result.risk["level"] == "medium"
        score = result.risk["score"]
        assert score == (1 * 1) + (2 * 2) + (3 * 3)


# ── Circular dependency ───────────────────────────────────────────


class TestCircularDependency:
    def test_direct_cycle(self):
        nodes = _make_nodes("a", "b")
        rels = _make_rels(("a", "IMPORTS", "b"), ("b", "IMPORTS", "a"))
        g = Graph(nodes, rels)
        result = analyze_impact(g, "a")
        assert len(result.direct_impact) == 1
        assert result.direct_impact[0].node.node_id == "b"
        assert len(result.indirect_impact) == 0

    def test_three_node_cycle(self):
        nodes = _make_nodes("a", "b", "c")
        rels = _make_rels(
            ("a", "IMPORTS", "b"),
            ("b", "IMPORTS", "c"),
            ("c", "IMPORTS", "a"),
        )
        g = Graph(nodes, rels)
        result = analyze_impact(g, "a")
        visited_ids = {a.node.node_id for a in result.direct_impact + result.indirect_impact}
        assert "a" not in visited_ids
        assert len(visited_ids) <= 2

    def test_cycle_no_infinite_loop(self):
        nodes = _make_nodes("a", "b", "c", "d")
        rels = _make_rels(
            ("a", "IMPORTS", "b"),
            ("b", "IMPORTS", "c"),
            ("c", "IMPORTS", "b"),
            ("c", "IMPORTS", "d"),
        )
        g = Graph(nodes, rels)
        result = analyze_impact(g, "d")
        assert result.metrics["total_affected"] <= 3

    def test_self_referencing_not_counted(self):
        nodes = _make_nodes("a")
        rels = _make_rels(("a", "IMPORTS", "a"))
        g = Graph(nodes, rels)
        result = analyze_impact(g, "a")
        assert len(result.direct_impact) == 0


# ── Diamond / fan-in / fan-out ────────────────────────────────────


class TestDiamondPattern:
    def test_fan_out_from_target(self):
        nodes = _make_nodes("target", "a", "b", "c")
        rels = _make_rels(
            ("a", "IMPORTS", "target"),
            ("b", "IMPORTS", "target"),
            ("c", "IMPORTS", "target"),
        )
        g = Graph(nodes, rels)
        result = analyze_impact(g, "target")
        assert len(result.direct_impact) == 3
        assert len(result.indirect_impact) == 0

    def test_fan_in_diamond(self):
        nodes = _make_nodes("a", "b", "c", "target")
        rels = _make_rels(
            ("a", "IMPORTS", "b"),
            ("a", "IMPORTS", "c"),
            ("b", "IMPORTS", "target"),
            ("c", "IMPORTS", "target"),
        )
        g = Graph(nodes, rels)
        result = analyze_impact(g, "target")
        assert len(result.direct_impact) == 2
        assert len(result.indirect_impact) == 1
        assert result.indirect_impact[0].node.node_id == "a"

    def test_shared_indirect(self):
        nodes = _make_nodes("a", "b", "c", "target")
        rels = _make_rels(
            ("a", "IMPORTS", "b"),
            ("a", "IMPORTS", "c"),
            ("b", "IMPORTS", "target"),
            ("c", "IMPORTS", "target"),
        )
        g = Graph(nodes, rels)
        result = analyze_impact(g, "target")
        all_ids = [n.node.node_id for n in result.direct_impact + result.indirect_impact]
        assert all_ids.count("a") == 1


# ── Mixed node types ──────────────────────────────────────────────


class TestMixedNodeTypes:
    def test_files_and_functions(self):
        nodes = [
            _node("file_a", "File", "a.ts"),
            _node("file_b", "File", "b.ts"),
            _node("fn_a", "Function", "foo"),
            _node("fn_b", "Function", "bar"),
        ]
        rels = _make_rels(
            ("file_a", "DEFINES", "fn_a"),
            ("file_b", "DEFINES", "fn_b"),
            ("fn_a", "CALLS", "fn_b"),
        )
        g = Graph(nodes, rels)
        result = analyze_impact(g, "fn_b")
        assert result.metrics["affected_functions"] == 1
        assert result.metrics["affected_files"] == 2

    def test_api_route_in_chain(self):
        nodes = [
            _node("route", "ApiRoute", "/api/users"),
            _node("svc", "Function", "getUsers"),
            _node("repo", "Function", "findUsers"),
        ]
        rels = _make_rels(
            ("route", "CALLS", "svc"),
            ("svc", "CALLS", "repo"),
        )
        g = Graph(nodes, rels)
        result = analyze_impact(g, "repo")
        assert len(result.direct_impact) == 1
        assert len(result.indirect_impact) == 1
        assert result.metrics["affected_apis"] == 1
        assert result.risk["score"] > 5

    def test_class_extends(self):
        nodes = [
            _node("base", "Class", "BaseService"),
            _node("child", "Class", "UserService"),
        ]
        rels = _make_rels(("child", "EXTENDS", "base"))
        g = Graph(nodes, rels)
        result = analyze_impact(g, "base")
        assert len(result.direct_impact) == 1
        assert result.metrics["affected_classes"] == 1

    def test_api_route_risk_bonus(self):
        nodes = [_node("api", "ApiRoute", "/"), _node("fn", "Function", "handler")]
        rels = _make_rels(("api", "CALLS", "fn"))
        g = Graph(nodes, rels)
        result = analyze_impact(g, "fn")
        assert result.risk["score"] >= 5

    def test_class_risk_bonus(self):
        nodes = [_node("base", "Class", "Base"), _node("child", "Class", "Child")]
        rels = _make_rels(("child", "EXTENDS", "base"))
        g = Graph(nodes, rels)
        result = analyze_impact(g, "base")
        assert result.risk["score"] == 7


# ── Max depth ─────────────────────────────────────────────────────


class TestMaxDepth:
    def test_limits_traversal(self):
        nodes = _make_nodes("a", "b", "c", "d", "e")
        rels = _make_rels(
            ("a", "IMPORTS", "b"),
            ("b", "IMPORTS", "c"),
            ("c", "IMPORTS", "d"),
            ("d", "IMPORTS", "e"),
        )
        g = Graph(nodes, rels)
        result = analyze_impact(g, "e", max_depth=2)
        assert result.metrics["dependency_depth"] <= 2

    def test_depth_one_limits_to_direct(self):
        nodes = _make_nodes("a", "b", "c")
        rels = _make_rels(("a", "IMPORTS", "b"), ("b", "IMPORTS", "c"))
        g = Graph(nodes, rels)
        result = analyze_impact(g, "c", max_depth=1)
        assert len(result.direct_impact) == 1
        assert len(result.indirect_impact) == 0


# ── Large graph ───────────────────────────────────────────────────


class TestLargeGraph:
    def test_wide_graph(self):
        nodes = _make_nodes("target")
        rels: List[Dict[str, Any]] = []
        for i in range(50):
            nid = f"dep_{i}"
            nodes.append(_node(nid, "Function", f"fn_{i}"))
            rels.append({"from_id": nid, "to_id": "target", "type": "CALLS"})
        g = Graph(nodes, rels)
        result = analyze_impact(g, "target")
        assert len(result.direct_impact) == 50
        assert len(result.indirect_impact) == 0
        assert result.metrics["total_affected"] == 50
        assert result.risk["score"] == 53

    def test_deep_graph(self):
        nodes: List[Dict[str, Any]] = []
        rels: List[Dict[str, Any]] = []
        for i in range(30):
            nodes.append(_node(f"n_{i}", "Function", f"fn_{i}"))
        for i in range(29):
            rels.append({"from_id": f"n_{i}", "to_id": f"n_{i + 1}", "type": "IMPORTS"})
        g = Graph(nodes, rels)
        result = analyze_impact(g, "n_29", max_depth=30)
        assert result.metrics["dependency_depth"] == 29
        assert result.metrics["total_affected"] == 29
        assert result.risk["level"] == "high"

    def test_complex_graph(self):
        nodes = [_node("root", "File", "root.ts")]
        rels: List[Dict[str, Any]] = []
        for i in range(20):
            nid = f"child_{i}"
            nodes.append(_node(nid, "Function", f"fn_{i}"))
            rels.append({"from_id": nid, "to_id": "root", "type": "CALLS"})
            for j in range(3):
                deep = f"deep_{i}_{j}"
                nodes.append(_node(deep, "Function", f"deep_{i}_{j}"))
                rels.append({"from_id": deep, "to_id": nid, "type": "IMPORTS"})
        g = Graph(nodes, rels)
        result = analyze_impact(g, "root")
        assert result.metrics["direct_dependencies"] == 20
        assert result.metrics["indirect_dependencies"] == 60
        assert result.risk["level"] == "high"


# ── Risk scoring ──────────────────────────────────────────────────


class TestRiskScoring:
    def test_low_risk(self):
        metrics = {
            "direct_dependencies": 1,
            "indirect_dependencies": 0,
            "dependency_depth": 1,
            "affected_apis": 0,
            "affected_classes": 0,
            "affected_files": 1,
            "total_affected": 1,
        }
        risk = _compute_risk(metrics)
        assert risk["level"] == "low"
        assert risk["score"] == 4

    def test_medium_risk(self):
        metrics = {
            "direct_dependencies": 3,
            "indirect_dependencies": 4,
            "dependency_depth": 3,
            "affected_apis": 0,
            "affected_classes": 0,
            "affected_files": 5,
            "total_affected": 7,
        }
        risk = _compute_risk(metrics)
        assert risk["level"] == "medium"

    def test_high_risk(self):
        metrics = {
            "direct_dependencies": 5,
            "indirect_dependencies": 10,
            "dependency_depth": 5,
            "affected_apis": 2,
            "affected_classes": 3,
            "affected_files": 10,
            "total_affected": 15,
        }
        risk = _compute_risk(metrics)
        assert risk["level"] == "high"
        assert risk["score"] > 20

    def test_formula_present(self):
        metrics = {"direct_dependencies": 0, "indirect_dependencies": 0, "dependency_depth": 0, "affected_apis": 0, "affected_classes": 0, "affected_files": 0, "total_affected": 0}
        risk = _compute_risk(metrics)
        assert "formula" in risk
        assert "score" in risk["formula"]

    def test_reasons_populated(self):
        metrics = {"direct_dependencies": 2, "indirect_dependencies": 3, "dependency_depth": 4, "affected_apis": 1, "affected_classes": 1, "affected_files": 5, "total_affected": 5}
        risk = _compute_risk(metrics)
        assert len(risk["reasons"]) > 0

    def test_empty_risk(self):
        metrics = {"direct_dependencies": 0, "indirect_dependencies": 0, "dependency_depth": 0, "affected_apis": 0, "affected_classes": 0, "affected_files": 0, "total_affected": 0}
        risk = _compute_risk(metrics)
        assert risk["level"] == "low"
        assert risk["score"] == 0
        assert len(risk["reasons"]) == 0


# ── ImpactNode ────────────────────────────────────────────────────


class TestImpactNode:
    def test_to_dict(self):
        n = ImpactNode("n1", "Function", "foo", {"line": 10})
        d = n.to_dict()
        assert d["node_id"] == "n1"
        assert d["label"] == "Function"
        assert d["name"] == "foo"
        assert d["line"] == 10

    def test_to_dict_empty_props(self):
        n = ImpactNode("n1", "File", "a.ts")
        d = n.to_dict()
        assert "node_id" in d
        assert len(d) == 3


# ── AffectedNode ──────────────────────────────────────────────────


class TestAffectedNode:
    def test_to_dict(self):
        n = ImpactNode("n1", "Function", "foo")
        a = AffectedNode(n, 2, ["target", "n1"])
        d = a.to_dict()
        assert d["depth"] == 2
        assert d["path"] == ["target", "n1"]
        assert d["node"]["node_id"] == "n1"


# ── ImpactResult ──────────────────────────────────────────────────


class TestImpactResult:
    def test_to_dict_empty(self):
        r = ImpactResult()
        d = r.to_dict()
        assert d["target"] is None
        assert d["direct_impact"] == []
        assert d["indirect_impact"] == []
        assert d["dependency_paths"] == []
        assert d["metrics"] == {}
        assert d["risk"] == {}

    def test_to_dict_populated(self):
        n = ImpactNode("a", "File", "a.ts")
        r = ImpactResult()
        r.target = n
        r.direct_impact = [AffectedNode(n, 1, ["a"])]
        r.metrics = {"total_affected": 1}
        r.risk = {"level": "low"}
        d = r.to_dict()
        assert d["target"]["node_id"] == "a"
        assert len(d["direct_impact"]) == 1
        assert d["metrics"]["total_affected"] == 1


# ── Duplicate path prevention ─────────────────────────────────────


class TestDuplicatePathPrevention:
    def test_diamond_no_duplicate_nodes(self):
        nodes = _make_nodes("a", "b", "c", "target")
        rels = _make_rels(
            ("a", "IMPORTS", "b"),
            ("a", "IMPORTS", "c"),
            ("b", "IMPORTS", "target"),
            ("c", "IMPORTS", "target"),
        )
        g = Graph(nodes, rels)
        result = analyze_impact(g, "target")
        all_affected = result.direct_impact + result.indirect_impact
        node_ids = [a.node.node_id for a in all_affected]
        assert node_ids.count("a") == 1

    def test_converging_paths(self):
        nodes = _make_nodes("a", "b", "c", "d", "target")
        rels = _make_rels(
            ("a", "IMPORTS", "b"),
            ("a", "IMPORTS", "c"),
            ("b", "IMPORTS", "target"),
            ("c", "IMPORTS", "target"),
            ("d", "IMPORTS", "b"),
        )
        g = Graph(nodes, rels)
        result = analyze_impact(g, "target")
        all_ids = {a.node.node_id for a in result.direct_impact + result.indirect_impact}
        assert all_ids == {"a", "b", "c", "d"}
