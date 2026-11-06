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


def _node(nid: str, label: str = "Function", name: str = "") -> Dict[str, Any]:
    return {"node_id": nid, "label": label, "name": name or nid}


def _rel(from_id: str, rel_type: str, to_id: str) -> Dict[str, Any]:
    return {"from_id": from_id, "to_id": to_id, "type": rel_type}


def _make_nodes(*ids: str, label: str = "Function") -> List[Dict[str, Any]]:
    return [{"node_id": nid, "label": label, "name": nid} for nid in ids]


def _make_rels(*triples: tuple) -> List[Dict[str, Any]]:
    return [{"from_id": s, "to_id": t, "type": r} for s, r, t in triples]


def _chain(n: int) -> tuple:
    nodes = [f"n_{i}" for i in range(n)]
    rels = [("n_" + str(i), "IMPORTS", "n_" + str(i + 1)) for i in range(n - 1)]
    return _make_nodes(*nodes), _make_rels(*rels)


# ── 1. No dependencies ────────────────────────────────────────────


class TestNoDependenciesExtensive:
    def test_empty_graph(self):
        g = Graph([], [])
        result = analyze_impact(g, "anything")
        assert result.target is None
        assert result.risk["level"] == "unknown"

    def test_single_isolated_node(self):
        g = Graph([_node("x")], [])
        result = analyze_impact(g, "x")
        assert result.target is not None
        assert result.target.node_id == "x"
        assert len(result.direct_impact) == 0
        assert len(result.indirect_impact) == 0
        assert result.metrics["total_affected"] == 0
        assert result.risk["level"] == "low"
        assert result.risk["score"] == 0
        assert result.dependency_paths == []

    def test_hundred_isolated_nodes(self):
        nodes = [_node(f"iso_{i}") for i in range(100)]
        g = Graph(nodes, [])
        result = analyze_impact(g, "iso_50")
        assert len(result.direct_impact) == 0
        assert result.metrics["total_affected"] == 0

    def test_target_not_in_graph(self):
        g = Graph([_node("a"), _node("b")], [])
        result = analyze_impact(g, "missing")
        assert result.target is None
        assert result.risk["level"] == "unknown"

    def test_multiple_components(self):
        nodes = _make_nodes("a", "b", "c", "d", "e", "f")
        rels = _make_rels(("a", "IMPORTS", "b"), ("d", "IMPORTS", "e"))
        g = Graph(nodes, rels)
        result = analyze_impact(g, "f")
        assert len(result.direct_impact) == 0
        assert len(result.indirect_impact) == 0


# ── 2. Direct dependency ──────────────────────────────────────────


class TestDirectDependencyExtensive:
    def test_single_caller(self):
        g = Graph(_make_nodes("caller", "target"), _make_rels(("caller", "CALLS", "target")))
        result = analyze_impact(g, "target")
        assert len(result.direct_impact) == 1
        assert result.direct_impact[0].node.node_id == "caller"
        assert result.direct_impact[0].depth == 1
        assert result.dependency_paths == [["target", "caller"]]

    def test_single_importer(self):
        g = Graph(_make_nodes("mod_a", "mod_b"), _make_rels(("mod_a", "IMPORTS", "mod_b")))
        result = analyze_impact(g, "mod_b")
        assert len(result.direct_impact) == 1
        assert result.metrics["direct_dependencies"] == 1
        assert result.risk["score"] == 4

    def test_multiple_rel_types_to_same_target(self):
        nodes = _make_nodes("a", "b")
        rels = _make_rels(("a", "IMPORTS", "b"), ("a", "CALLS", "b"), ("a", "EXTENDS", "b"))
        g = Graph(nodes, rels)
        result = analyze_impact(g, "b")
        assert len(result.direct_impact) == 1
        incoming = g.get_incoming("b")
        assert len(incoming) == 3

    def test_extends_relationship(self):
        g = Graph(
            [_node("base", "Class"), _node("child", "Class")],
            [_rel("child", "EXTENDS", "base")],
        )
        result = analyze_impact(g, "base")
        assert len(result.direct_impact) == 1
        assert result.direct_impact[0].node.label == "Class"


# ── 3. Multiple direct dependencies ───────────────────────────────


class TestMultipleDirectDependenciesExtensive:
    def test_two_direct(self):
        g = Graph(
            _make_nodes("a", "b", "target"),
            _make_rels(("a", "IMPORTS", "target"), ("b", "CALLS", "target")),
        )
        result = analyze_impact(g, "target")
        assert len(result.direct_impact) == 2
        ids = {d.node.node_id for d in result.direct_impact}
        assert ids == {"a", "b"}

    def test_ten_direct(self):
        nodes = [_node("target")]
        rels = []
        for i in range(10):
            nid = f"caller_{i}"
            nodes.append(_node(nid))
            rels.append(_rel(nid, "CALLS", "target"))
        g = Graph(nodes, rels)
        result = analyze_impact(g, "target")
        assert len(result.direct_impact) == 10
        assert result.metrics["direct_dependencies"] == 10
        assert result.risk["level"] == "medium"

    def test_fifty_direct(self):
        nodes = [_node("target")]
        rels = []
        for i in range(50):
            nid = f"c_{i}"
            nodes.append(_node(nid))
            rels.append(_rel(nid, "IMPORTS", "target"))
        g = Graph(nodes, rels)
        result = analyze_impact(g, "target")
        assert len(result.direct_impact) == 50
        assert result.risk["level"] == "high"

    def test_direct_with_mixed_types(self):
        nodes = [
            _node("target"),
            _node("fn1", "Function"),
            _node("cls1", "Class"),
            _node("file1", "File"),
            _node("api1", "ApiRoute"),
        ]
        rels = [
            _rel("fn1", "CALLS", "target"),
            _rel("cls1", "EXTENDS", "target"),
            _rel("file1", "IMPORTS", "target"),
            _rel("api1", "CALLS", "target"),
        ]
        g = Graph(nodes, rels)
        result = analyze_impact(g, "target")
        assert len(result.direct_impact) == 4
        labels = {d.node.label for d in result.direct_impact}
        assert labels == {"Function", "Class", "File", "ApiRoute"}


# ── 4. Deep dependency chain ──────────────────────────────────────


class TestDeepChainExtensive:
    def test_linear_3(self):
        g = Graph(*_chain(3))
        result = analyze_impact(g, "n_2")
        assert len(result.direct_impact) == 1
        assert len(result.indirect_impact) == 1
        assert result.metrics["dependency_depth"] == 2

    def test_linear_10(self):
        g = Graph(*_chain(10))
        result = analyze_impact(g, "n_9", max_depth=15)
        assert result.metrics["dependency_depth"] == 9
        assert len(result.direct_impact) == 1
        assert len(result.indirect_impact) == 8

    def test_linear_20(self):
        g = Graph(*_chain(20))
        result = analyze_impact(g, "n_19", max_depth=25)
        assert result.metrics["dependency_depth"] == 19
        assert result.metrics["total_affected"] == 19

    def test_chain_depths_are_correct(self):
        g = Graph(*_chain(5))
        result = analyze_impact(g, "n_4", max_depth=10)
        direct = {a.node.node_id: a.depth for a in result.direct_impact}
        indirect = {a.node.node_id: a.depth for a in result.indirect_impact}
        assert direct == {"n_3": 1}
        assert indirect == {"n_2": 2, "n_1": 3, "n_0": 4}

    def test_chain_paths_complete(self):
        g = Graph(*_chain(4))
        result = analyze_impact(g, "n_3", max_depth=10)
        paths = sorted(result.dependency_paths, key=len)
        assert ["n_3", "n_2"] in result.dependency_paths
        assert ["n_3", "n_2", "n_1"] in result.dependency_paths
        assert ["n_3", "n_2", "n_1", "n_0"] in result.dependency_paths
        assert len(paths) == 3

    def test_chain_risk_increases_with_depth(self):
        g3 = Graph(*_chain(3))
        r3 = analyze_impact(g3, "n_2")
        g6 = Graph(*_chain(6))
        r6 = analyze_impact(g6, "n_5")
        assert r6.risk["score"] > r3.risk["score"]


# ── 5. Circular dependencies ──────────────────────────────────────


class TestCircularDependenciesExtensive:
    def test_two_node_cycle(self):
        nodes = _make_nodes("a", "b")
        rels = _make_rels(("a", "IMPORTS", "b"), ("b", "IMPORTS", "a"))
        g = Graph(nodes, rels)
        result = analyze_impact(g, "a")
        ids = {d.node.node_id for d in result.direct_impact + result.indirect_impact}
        assert "a" not in ids
        assert "b" in ids

    def test_three_node_cycle(self):
        nodes = _make_nodes("a", "b", "c")
        rels = _make_rels(("a", "IMPORTS", "b"), ("b", "IMPORTS", "c"), ("c", "IMPORTS", "a"))
        g = Graph(nodes, rels)
        result = analyze_impact(g, "a")
        ids = {d.node.node_id for d in result.direct_impact + result.indirect_impact}
        assert "a" not in ids
        assert len(ids) <= 2

    def test_cycle_with_larger_graph(self):
        nodes = _make_nodes("a", "b", "c", "d", "e")
        rels = _make_rels(
            ("a", "IMPORTS", "b"),
            ("b", "IMPORTS", "c"),
            ("c", "IMPORTS", "b"),
            ("c", "IMPORTS", "d"),
            ("d", "IMPORTS", "e"),
        )
        g = Graph(nodes, rels)
        result = analyze_impact(g, "e")
        ids = {d.node.node_id for d in result.direct_impact + result.indirect_impact}
        assert "e" not in ids
        assert result.metrics["total_affected"] <= 4

    def test_self_loop_ignored(self):
        g = Graph([_node("a")], [_rel("a", "IMPORTS", "a")])
        result = analyze_impact(g, "a")
        assert len(result.direct_impact) == 0

    def test_cycle_with_branches(self):
        nodes = _make_nodes("a", "b", "c", "x")
        rels = _make_rels(
            ("a", "IMPORTS", "b"),
            ("b", "IMPORTS", "c"),
            ("c", "IMPORTS", "a"),
            ("x", "IMPORTS", "a"),
        )
        g = Graph(nodes, rels)
        result = analyze_impact(g, "a")
        ids = {d.node.node_id for d in result.direct_impact + result.indirect_impact}
        assert "x" in ids

    def test_no_infinite_loop_large_cycle(self):
        nodes = [f"c_{i}" for i in range(50)]
        node_dicts = [{"node_id": n, "label": "Function", "name": n} for n in nodes]
        rels = []
        for i in range(49):
            rels.append({"from_id": f"c_{i}", "to_id": f"c_{i+1}", "type": "IMPORTS"})
        rels.append({"from_id": "c_49", "to_id": "c_0", "type": "IMPORTS"})
        g = Graph(node_dicts, rels)
        result = analyze_impact(g, "c_0")
        assert result.metrics["total_affected"] <= 49


# ── 6. Duplicate paths ───────────────────────────────────────────


class TestDuplicatePathsExtensive:
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

    def test_double_diamond(self):
        nodes = _make_nodes("root", "l1a", "l1b", "l2a", "l2b", "target")
        rels = _make_rels(
            ("root", "IMPORTS", "l1a"),
            ("root", "IMPORTS", "l1b"),
            ("l1a", "IMPORTS", "l2a"),
            ("l1b", "IMPORTS", "l2b"),
            ("l2a", "IMPORTS", "target"),
            ("l2b", "IMPORTS", "target"),
        )
        g = Graph(nodes, rels)
        result = analyze_impact(g, "target")
        ids = [a.node.node_id for a in result.direct_impact + result.indirect_impact]
        assert ids.count("root") == 1

    def test_many_paths_to_one_node(self):
        nodes = [_node("target")]
        rels = []
        for i in range(5):
            mid = f"mid_{i}"
            nodes.append(_node(mid))
            rels.append(_rel(mid, "IMPORTS", "target"))
            nodes.append(_node(f"src_{i}"))
            rels.append(_rel(f"src_{i}", "IMPORTS", mid))
            rels.append(_rel(f"src_{i}", "IMPORTS", "target"))
        g = Graph(nodes, rels)
        result = analyze_impact(g, "target")
        ids = [a.node.node_id for a in result.direct_impact + result.indirect_impact]
        for i in range(5):
            assert ids.count(f"src_{i}") == 1

    def test_convergent_diamond_paths(self):
        nodes = _make_nodes("a", "b", "c", "d", "e", "target")
        rels = _make_rels(
            ("a", "IMPORTS", "b"),
            ("a", "IMPORTS", "c"),
            ("b", "IMPORTS", "d"),
            ("c", "IMPORTS", "d"),
            ("d", "IMPORTS", "target"),
            ("e", "IMPORTS", "target"),
        )
        g = Graph(nodes, rels)
        result = analyze_impact(g, "target")
        ids = {a.node.node_id for a in result.direct_impact + result.indirect_impact}
        assert len(ids) == 5
        assert ids == {"a", "b", "c", "d", "e"}


# ── 7. Large dependency graph ─────────────────────────────────────


class TestLargeGraphExtensive:
    def test_wide_100(self):
        nodes = [_node("target")]
        rels = []
        for i in range(100):
            nid = f"d_{i}"
            nodes.append(_node(nid))
            rels.append(_rel(nid, "CALLS", "target"))
        g = Graph(nodes, rels)
        result = analyze_impact(g, "target")
        assert len(result.direct_impact) == 100
        assert result.metrics["total_affected"] == 100
        assert result.risk["level"] == "high"

    def test_deep_30(self):
        g = Graph(*_chain(30))
        result = analyze_impact(g, "n_29", max_depth=35)
        assert result.metrics["dependency_depth"] == 29
        assert result.metrics["total_affected"] == 29
        assert result.risk["level"] == "high"

    def test_wide_with_depth(self):
        nodes = [_node("target")]
        rels = []
        for i in range(10):
            mid = f"mid_{i}"
            nodes.append(_node(mid))
            rels.append(_rel(mid, "IMPORTS", "target"))
            for j in range(5):
                src = f"src_{i}_{j}"
                nodes.append(_node(src))
                rels.append(_rel(src, "IMPORTS", mid))
        g = Graph(nodes, rels)
        result = analyze_impact(g, "target")
        assert result.metrics["direct_dependencies"] == 10
        assert result.metrics["indirect_dependencies"] == 50
        assert result.metrics["dependency_depth"] == 2

    def test_tree_structure(self):
        nodes = [_node("root")]
        rels = []
        for i in range(3):
            n1 = f"l1_{i}"
            nodes.append(_node(n1))
            rels.append(_rel(n1, "IMPORTS", "root"))
            for j in range(3):
                n2 = f"l2_{i}_{j}"
                nodes.append(_node(n2))
                rels.append(_rel(n2, "IMPORTS", n1))
        g = Graph(nodes, rels)
        result = analyze_impact(g, "root")
        assert result.metrics["direct_dependencies"] == 3
        assert result.metrics["indirect_dependencies"] == 9
        assert result.metrics["dependency_depth"] == 2

    def test_grid_graph(self):
        nodes = []
        rels = []
        size = 10
        for r in range(size):
            for c in range(size):
                nodes.append(_node(f"cell_{r}_{c}"))
                if c > 0:
                    rels.append(_rel(f"cell_{r}_{c}", "IMPORTS", f"cell_{r}_{c-1}"))
                if r > 0:
                    rels.append(_rel(f"cell_{r}_{c}", "IMPORTS", f"cell_{r-1}_{c}"))
        g = Graph(nodes, rels)
        result = analyze_impact(g, "cell_0_0")
        assert result.metrics["total_affected"] > 0

    def test_performance_large_graph(self):
        nodes = [_node("t")]
        rels = []
        for i in range(200):
            nid = f"n_{i}"
            nodes.append(_node(nid))
            rels.append(_rel(nid, "CALLS", "t"))
        g = Graph(nodes, rels)
        result = analyze_impact(g, "t")
        assert len(result.direct_impact) == 200


# ── 8. File-level impact ─────────────────────────────────────────


class TestFileLevelImpact:
    def test_file_imports_file(self):
        nodes = [_node("file_a.ts", "File"), _node("file_b.ts", "File")]
        rels = [_rel("file_a.ts", "IMPORTS", "file_b.ts")]
        g = Graph(nodes, rels)
        result = analyze_impact(g, "file_b.ts")
        assert len(result.direct_impact) == 1
        assert result.direct_impact[0].node.label == "File"
        assert result.metrics["affected_files"] == 1

    def test_file_reexport_chain(self):
        nodes = [_node(f"f{i}.ts", "File") for i in range(5)]
        rels = [_rel(f"f{i}.ts", "REEXPORTS", f"f{i+1}.ts") for i in range(4)]
        g = Graph(nodes, rels)
        result = analyze_impact(g, "f4.ts")
        assert result.metrics["affected_files"] == 4
        assert result.metrics["dependency_depth"] == 4

    def test_file_with_functions(self):
        nodes = [
            _node("utils.ts", "File"),
            _node("helpers.ts", "File"),
            _node("formatDate", "Function"),
            _node("parseCSV", "Function"),
        ]
        rels = [
            _rel("helpers.ts", "IMPORTS", "utils.ts"),
            _rel("helpers.ts", "DEFINES", "formatDate"),
            _rel("helpers.ts", "DEFINES", "parseCSV"),
            _rel("parseCSV", "CALLS", "formatDate"),
        ]
        g = Graph(nodes, rels)
        result = analyze_impact(g, "formatDate")
        assert result.metrics["affected_files"] >= 1

    def test_cross_file_function_calls(self):
        nodes = [
            _node("a.ts", "File"),
            _node("b.ts", "File"),
            _node("funcA", "Function"),
            _node("funcB", "Function"),
        ]
        rels = [
            _rel("a.ts", "IMPORTS", "b.ts"),
            _rel("a.ts", "DEFINES", "funcA"),
            _rel("b.ts", "DEFINES", "funcB"),
            _rel("funcA", "CALLS", "funcB"),
        ]
        g = Graph(nodes, rels)
        result = analyze_impact(g, "funcB")
        ids = {d.node.node_id for d in result.direct_impact}
        assert "funcA" in ids
        assert "b.ts" in ids
        assert len(result.direct_impact) == 2


# ── 9. Function-level impact ─────────────────────────────────────


class TestFunctionLevelImpact:
    def test_function_calls_function(self):
        nodes = [_node("caller", "Function"), _node("callee", "Function")]
        rels = [_rel("caller", "CALLS", "callee")]
        g = Graph(nodes, rels)
        result = analyze_impact(g, "callee")
        assert len(result.direct_impact) == 1
        assert result.metrics["affected_functions"] == 1

    def test_function_chain(self):
        nodes = [_node(f"fn_{i}", "Function") for i in range(6)]
        rels = [_rel(f"fn_{i}", "CALLS", f"fn_{i+1}") for i in range(5)]
        g = Graph(nodes, rels)
        result = analyze_impact(g, "fn_5")
        assert result.metrics["affected_functions"] == 5
        assert result.metrics["dependency_depth"] == 5

    def test_function_called_by_many(self):
        nodes = [_node("target_fn", "Function")]
        rels = []
        for i in range(20):
            nid = f"caller_{i}"
            nodes.append(_node(nid, "Function"))
            rels.append(_rel(nid, "CALLS", "target_fn"))
        g = Graph(nodes, rels)
        result = analyze_impact(g, "target_fn")
        assert result.metrics["affected_functions"] == 20

    def test_async_function(self):
        nodes = [_node("asyncFn", "Function", "asyncFn"), _node("syncFn", "Function", "syncFn")]
        rels = [_rel("syncFn", "CALLS", "asyncFn")]
        g = Graph(nodes, rels)
        result = analyze_impact(g, "asyncFn")
        assert len(result.direct_impact) == 1

    def test_method_level(self):
        nodes = [
            _node("UserService", "Class"),
            _node("UserRepo", "Class"),
            _node("findById", "Method"),
            _node("save", "Method"),
        ]
        rels = [
            _rel("findById", "CALLS", "save"),
            _rel("UserService", "DEFINES", "findById"),
            _rel("UserRepo", "DEFINES", "save"),
        ]
        g = Graph(nodes, rels)
        result = analyze_impact(g, "save")
        ids = {d.node.node_id for d in result.direct_impact}
        assert "findById" in ids
        assert "UserRepo" in ids
        assert len(result.direct_impact) == 2

    def test_mixed_function_and_file(self):
        nodes = [
            _node("lib.ts", "File"),
            _node("helper.ts", "File"),
            _node("getData", "Function"),
            _node("processData", "Function"),
        ]
        rels = [
            _rel("helper.ts", "IMPORTS", "lib.ts"),
            _rel("getData", "CALLS", "processData"),
            _rel("helper.ts", "DEFINES", "getData"),
            _rel("lib.ts", "DEFINES", "processData"),
        ]
        g = Graph(nodes, rels)
        result = analyze_impact(g, "processData")
        ids = {d.node.node_id for d in result.direct_impact}
        assert "getData" in ids
        assert "lib.ts" in ids
        assert len(result.direct_impact) == 2
        assert result.metrics["affected_functions"] == 1


# ── 10. API-level impact ─────────────────────────────────────────


class TestApiLevelImpact:
    def test_api_calls_function(self):
        nodes = [_node("/api/users", "ApiRoute"), _node("getUsers", "Function")]
        rels = [_rel("/api/users", "CALLS", "getUsers")]
        g = Graph(nodes, rels)
        result = analyze_impact(g, "getUsers")
        assert len(result.direct_impact) == 1
        assert result.direct_impact[0].node.label == "ApiRoute"
        assert result.metrics["affected_apis"] == 1

    def test_api_in_chain(self):
        nodes = [
            _node("/api/orders", "ApiRoute"),
            _node("orderService", "Function"),
            _node("orderRepo", "Function"),
            _node("db", "Function"),
        ]
        rels = [
            _rel("/api/orders", "CALLS", "orderService"),
            _rel("orderService", "CALLS", "orderRepo"),
            _rel("orderRepo", "CALLS", "db"),
        ]
        g = Graph(nodes, rels)
        result = analyze_impact(g, "db")
        assert result.metrics["affected_apis"] == 1
        assert len(result.indirect_impact) == 2
        assert result.risk["score"] > 10

    def test_multiple_apis(self):
        nodes = [_node("shared", "Function")]
        rels = []
        for i in range(5):
            api = f"/api/resource_{i}"
            nodes.append(_node(api, "ApiRoute"))
            rels.append(_rel(api, "CALLS", "shared"))
        g = Graph(nodes, rels)
        result = analyze_impact(g, "shared")
        assert result.metrics["affected_apis"] == 5

    def test_api_risk_bonus(self):
        nodes = [_node("/api/x", "ApiRoute"), _node("fn", "Function")]
        rels = [_rel("/api/x", "CALLS", "fn")]
        g = Graph(nodes, rels)
        result = analyze_impact(g, "fn")
        assert result.risk["score"] >= 5
        assert any("API" in r.upper() for r in result.risk.get("reasons", []))

    def test_full_stack_impact(self):
        nodes = [
            _node("/api/auth/login", "ApiRoute"),
            _node("authController", "Function"),
            _node("authService", "Function"),
            _node("User", "Class"),
            _node("db.query", "Function"),
        ]
        rels = [
            _rel("/api/auth/login", "CALLS", "authController"),
            _rel("authController", "CALLS", "authService"),
            _rel("authService", "CALLS", "User"),
            _rel("User", "CALLS", "db.query"),
        ]
        g = Graph(nodes, rels)
        result = analyze_impact(g, "db.query")
        assert result.metrics["affected_apis"] == 1
        assert result.metrics["affected_classes"] == 1
        assert result.metrics["affected_functions"] == 2
        assert result.risk["level"] == "high"

    def test_api_route_not_affected_when_target_is_above(self):
        nodes = [_node("/api/data", "ApiRoute"), _node("handler", "Function")]
        rels = [_rel("/api/data", "CALLS", "handler")]
        g = Graph(nodes, rels)
        result = analyze_impact(g, "handler")
        assert result.metrics["affected_apis"] == 1

    def test_api_extends_class(self):
        nodes = [
            _node("/api/base", "ApiRoute"),
            _node("BaseHandler", "Class"),
            _node("ExtendedHandler", "Class"),
        ]
        rels = [
            _rel("/api/base", "CALLS", "BaseHandler"),
            _rel("ExtendedHandler", "EXTENDS", "BaseHandler"),
        ]
        g = Graph(nodes, rels)
        result = analyze_impact(g, "BaseHandler")
        assert result.metrics["affected_apis"] == 1
        assert result.metrics["affected_classes"] == 1


# ── Metrics computation ───────────────────────────────────────────


class TestMetricsComputation:
    def test_metrics_with_all_types(self):
        nodes = [
            _node("target"),
            _node("f1", "Function"),
            _node("f2", "Function"),
            _node("c1", "Class"),
            _node("file1", "File"),
            _node("/api/x", "ApiRoute"),
            _node("m1", "Method"),
        ]
        rels = [
            _rel("f1", "CALLS", "target"),
            _rel("f2", "CALLS", "target"),
            _rel("c1", "EXTENDS", "target"),
            _rel("/api/x", "CALLS", "target"),
            _rel("m1", "CALLS", "target"),
        ]
        g = Graph(nodes, rels)
        result = analyze_impact(g, "target")
        m = result.metrics
        assert m["affected_functions"] >= 2
        assert m["affected_classes"] >= 1
        assert m["affected_apis"] >= 1

    def test_metrics_counts_only_affected(self):
        nodes = [
            _node("target"),
            _node("affected_fn", "Function"),
            _node("unaffected_fn", "Function"),
        ]
        rels = [_rel("affected_fn", "CALLS", "target")]
        g = Graph(nodes, rels)
        result = analyze_impact(g, "target")
        assert result.metrics["affected_functions"] == 1

    def test_metrics_empty_graph(self):
        g = Graph([], [])
        result = analyze_impact(g, "x")
        m = result.metrics
        assert m.get("total_affected", 0) == 0


# ── Risk scoring extensive ───────────────────────────────────────


class TestRiskScoringExtensive:
    def test_zero_risk(self):
        risk = _compute_risk({
            "direct_dependencies": 0, "indirect_dependencies": 0,
            "dependency_depth": 0, "affected_apis": 0,
            "affected_classes": 0, "affected_files": 0, "total_affected": 0,
        })
        assert risk["level"] == "low"
        assert risk["score"] == 0

    def test_boundary_low_medium(self):
        risk = _compute_risk({
            "direct_dependencies": 2, "indirect_dependencies": 2,
            "dependency_depth": 2, "affected_apis": 0,
            "affected_classes": 0, "affected_files": 4, "total_affected": 4,
        })
        assert risk["score"] == 12
        assert risk["level"] == "medium"

    def test_boundary_medium_high(self):
        risk = _compute_risk({
            "direct_dependencies": 3, "indirect_dependencies": 5,
            "dependency_depth": 3, "affected_apis": 1,
            "affected_classes": 1, "affected_files": 8, "total_affected": 8,
        })
        assert risk["score"] == 30
        assert risk["level"] == "high"

    def test_api_bonus(self):
        base = _compute_risk({
            "direct_dependencies": 1, "indirect_dependencies": 0,
            "dependency_depth": 1, "affected_apis": 0,
            "affected_classes": 0, "affected_files": 1, "total_affected": 1,
        })
        with_api = _compute_risk({
            "direct_dependencies": 1, "indirect_dependencies": 0,
            "dependency_depth": 1, "affected_apis": 1,
            "affected_classes": 0, "affected_files": 1, "total_affected": 1,
        })
        assert with_api["score"] - base["score"] == 5

    def test_class_bonus(self):
        base = _compute_risk({
            "direct_dependencies": 1, "indirect_dependencies": 0,
            "dependency_depth": 1, "affected_apis": 0,
            "affected_classes": 0, "affected_files": 1, "total_affected": 1,
        })
        with_cls = _compute_risk({
            "direct_dependencies": 1, "indirect_dependencies": 0,
            "dependency_depth": 1, "affected_apis": 0,
            "affected_classes": 1, "affected_files": 1, "total_affected": 1,
        })
        assert with_cls["score"] - base["score"] == 3

    def test_risk_has_required_keys(self):
        risk = _compute_risk({
            "direct_dependencies": 1, "indirect_dependencies": 1,
            "dependency_depth": 1, "affected_apis": 0,
            "affected_classes": 0, "affected_files": 2, "total_affected": 2,
        })
        assert "level" in risk
        assert "score" in risk
        assert "color" in risk
        assert "reasons" in risk
        assert "summary" in risk
        assert "formula" in risk

    def test_reasons_populated_for_nonzero(self):
        risk = _compute_risk({
            "direct_dependencies": 3, "indirect_dependencies": 2,
            "dependency_depth": 3, "affected_apis": 1,
            "affected_classes": 1, "affected_files": 5, "total_affected": 5,
        })
        assert len(risk["reasons"]) > 0

    def test_reasons_empty_for_zero(self):
        risk = _compute_risk({
            "direct_dependencies": 0, "indirect_dependencies": 0,
            "dependency_depth": 0, "affected_apis": 0,
            "affected_classes": 0, "affected_files": 0, "total_affected": 0,
        })
        assert len(risk["reasons"]) == 0


# ── Max depth boundary ───────────────────────────────────────────


class TestMaxDepthBoundary:
    def test_depth_0_finds_nothing(self):
        g = Graph(*_chain(3))
        result = analyze_impact(g, "n_2", max_depth=0)
        assert len(result.direct_impact) == 0
        assert len(result.indirect_impact) == 0

    def test_depth_1_finds_direct_only(self):
        g = Graph(*_chain(5))
        result = analyze_impact(g, "n_4", max_depth=1)
        assert len(result.direct_impact) == 1
        assert len(result.indirect_impact) == 0

    def test_depth_exact_chain_length(self):
        g = Graph(*_chain(4))
        result = analyze_impact(g, "n_3", max_depth=3)
        assert len(result.direct_impact) == 1
        assert len(result.indirect_impact) == 2

    def test_depth_exceeds_chain(self):
        g = Graph(*_chain(4))
        result = analyze_impact(g, "n_3", max_depth=100)
        assert result.metrics["total_affected"] == 3

    def test_default_depth(self):
        g = Graph(*_chain(10))
        result = analyze_impact(g, "n_9")
        assert result.metrics["dependency_depth"] == 9


# ── Serialization ─────────────────────────────────────────────────


class TestSerializationExtensive:
    def test_result_full_roundtrip(self):
        nodes = [_node("target"), _node("a", "Function"), _node("b", "Class")]
        rels = [_rel("a", "CALLS", "target"), _rel("b", "EXTENDS", "target")]
        g = Graph(nodes, rels)
        result = analyze_impact(g, "target")
        d = result.to_dict()

        assert "target" in d
        assert "direct_impact" in d
        assert "indirect_impact" in d
        assert "dependency_paths" in d
        assert "metrics" in d
        assert "risk" in d
        assert d["target"]["node_id"] == "target"
        assert len(d["direct_impact"]) == 2
        assert isinstance(d["risk"]["score"], int)

    def test_node_to_dict_with_many_props(self):
        n = ImpactNode("id1", "Function", "myFunc", {
            "file_path": "src/utils.ts",
            "start_line": 10,
            "end_line": 25,
            "is_async": True,
            "is_exported": True,
        })
        d = n.to_dict()
        assert d["file_path"] == "src/utils.ts"
        assert d["start_line"] == 10
        assert d["is_async"] is True

    def test_affected_node_to_dict(self):
        n = ImpactNode("n", "File", "f.ts")
        a = AffectedNode(n, 3, ["target", "mid", "n"])
        d = a.to_dict()
        assert d["depth"] == 3
        assert d["path"] == ["target", "mid", "n"]
        assert d["node"]["node_id"] == "n"
