"""In-memory graph store — lightweight drop-in for Neo4j in dev/test.

When NEO4J_PASSWORD is not set, graph.py uses this module instead of Neo4j.
Supports the subset of Cypher queries used by DevPilot's graph service.
"""

from __future__ import annotations

import json
import os
import re
from contextlib import contextmanager
from typing import Any, Dict, Iterator, List, Optional

_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
_GRAPH_FILE = os.path.join(_DATA_DIR, "graph.json")


class InMemoryGraph:
    """Stores nodes and relationships in Python dicts/lists."""

    def __init__(self) -> None:
        self._nodes: Dict[str, Dict[str, Any]] = {}
        self._rels: List[Dict[str, Any]] = []
        self._suspended = False
        self._dirty = False
        self._load()

    def session(self) -> _Session:
        return _Session(self)

    def close(self) -> None:
        if self._dirty:
            self._flush()

    def _save(self) -> None:
        if self._suspended:
            self._dirty = True
            return
        self._flush()

    def _flush(self) -> None:
        try:
            os.makedirs(_DATA_DIR, exist_ok=True)
            data = {"nodes": self._nodes, "rels": self._rels}
            with open(_GRAPH_FILE, "w") as f:
                json.dump(data, f)
            self._dirty = False
        except Exception:
            pass

    @contextmanager
    def suspended_saves(self) -> Iterator[None]:
        """Batch many mutations into a single disk write.

        Graph builds touch thousands of nodes/relationships. Writing the whole
        JSON file on every merge is quadratic; suspend writes during the build
        and persist once when the outer context exits.
        """
        previous = self._suspended
        self._suspended = True
        try:
            yield
        finally:
            self._suspended = previous
            if not self._suspended and self._dirty:
                self._flush()

    def _load(self) -> None:
        if not os.path.exists(_GRAPH_FILE):
            return
        try:
            with open(_GRAPH_FILE) as f:
                data = json.load(f)
            self._nodes = data.get("nodes", {})
            self._rels = data.get("rels", [])
        except Exception:
            pass


class _Record:
    """Mimics Neo4j Record — supports dict(record)."""

    __slots__ = ("_data",)

    def __init__(self, data: Dict[str, Any]) -> None:
        self._data = data

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __iter__(self):
        return iter(self._data)

    def items(self):
        return self._data.items()

    def keys(self):
        return self._data.keys()

    def values(self):
        return self._data.values()


class _Result:
    """Mimics Neo4j Result — iterable of Records."""

    __slots__ = ("_records",)

    def __init__(self, records: List[_Record]) -> None:
        self._records = records

    def __iter__(self):
        return iter(self._records)

    def __len__(self) -> int:
        return len(self._records)

    def __bool__(self) -> bool:
        return len(self._records) > 0

    def __getitem__(self, index: int) -> _Record:
        return self._records[index]

    def data(self) -> List[Dict[str, Any]]:
        return [dict(r._data) for r in self._records]


class _Session:
    """Executes the Cypher subset used by DevPilot against in-memory data."""

    __slots__ = ("_g",)

    def __init__(self, graph: InMemoryGraph) -> None:
        self._g = graph

    def run(self, query: str, **params: Any) -> _Result:
        q = " ".join(query.split())

        if "CREATE CONSTRAINT" in q or "CREATE INDEX" in q:
            return _Result([])

        if "DETACH DELETE" in q:
            return self._handle_delete(q, params)

        if "]->(" in q and "MERGE" in q:
            return self._handle_merge_rel(q, params)

        if q.startswith("MERGE"):
            return self._handle_merge_node(q, params)

        if "count(" in q.lower():
            return self._handle_aggregate(q, params)

        if re.search(r"\)-\[", q) or re.search(r"\]->\(", q):
            return self._handle_traverse(q, params)

        if q.startswith("MATCH"):
            return self._handle_lookup(q, params)

        return _Result([])

    def close(self) -> None:
        pass

    # ── MERGE node ──────────────────────────────────────────────

    def _handle_merge_node(self, q: str, params: Dict[str, Any]) -> _Result:
        m = re.search(r"MERGE \(\w+:(\w+)\s*\{(\w+):\s*\$(\w+)\}", q)
        if not m:
            return _Result([])
        label, key, param_name = m.group(1), m.group(2), m.group(3)
        key_val = params.get(param_name)

        node = None
        for n in self._g._nodes.values():
            if n.get("_label") == label and n.get(key) == key_val:
                node = n
                break

        if node is None:
            node_id = params.get("node_id", key_val)
            node = {"_label": label, key: key_val}
            self._g._nodes[node_id] = node

        for pm in re.finditer(r"\w+\.(\w+)\s*=\s*\$(\w+)", q):
            prop, pname = pm.group(1), pm.group(2)
            node[prop] = params.get(pname)

        self._g._save()
        return _Result([])

    # ── MERGE relationship ──────────────────────────────────────

    def _handle_merge_rel(self, q: str, params: Dict[str, Any]) -> _Result:
        from_id = params.get("from_id")
        to_id = params.get("to_id")
        if not from_id or not to_id:
            return _Result([])

        rm = re.search(r"MERGE \(\w+\)-\[(\w+):(\w+)", q)
        if not rm:
            return _Result([])
        rel_type = rm.group(2)

        rel_props: Dict[str, Any] = {}
        merge_part = q.split("MERGE", 1)[1] if "MERGE" in q else ""
        prop_m = re.search(r"\{(\w+):\s*\$(\w+)\}", merge_part)
        if prop_m:
            rel_props[prop_m.group(1)] = params.get(prop_m.group(2))

        for r in self._g._rels:
            if (
                r["_from"] == from_id
                and r["_to"] == to_id
                and r["_type"] == rel_type
            ):
                return _Result([])

        new_rel: Dict[str, Any] = {
            "_from": from_id,
            "_to": to_id,
            "_type": rel_type,
        }
        new_rel.update(rel_props)
        self._g._rels.append(new_rel)
        self._g._save()
        return _Result([])

    # ── DETACH DELETE ───────────────────────────────────────────

    def _handle_delete(self, q: str, params: Dict[str, Any]) -> _Result:
        props = self._parse_match_props(q, params)
        to_delete = [
            nid
            for nid, n in self._g._nodes.items()
            if all(n.get(k) == v for k, v in props.items())
        ]
        for nid in to_delete:
            del self._g._nodes[nid]
        self._g._rels = [
            r
            for r in self._g._rels
            if r["_from"] not in to_delete and r["_to"] not in to_delete
        ]
        self._g._save()
        return _Result([])

    # ── Aggregate ───────────────────────────────────────────────

    def _handle_aggregate(self, q: str, params: Dict[str, Any]) -> _Result:
        props = self._parse_match_props(q, params)

        if re.search(r"\[r\]->", q):
            repo_id = props.get("repo_id")
            filtered = [
                r
                for r in self._g._rels
                if self._g._nodes.get(r["_from"], {}).get("repo_id") == repo_id
                and self._g._nodes.get(r["_to"], {}).get("repo_id") == repo_id
            ]
            groups: Dict[str, int] = {}
            for rel in filtered:
                groups[rel["_type"]] = groups.get(rel["_type"], 0) + 1
            return _Result(
                [_Record({"rel_type": k, "count": v}) for k, v in groups.items()]
            )

        filtered = [
            n
            for n in self._g._nodes.values()
            if all(n.get(k) == v for k, v in props.items())
        ]
        if "labels(n)" in q:
            groups2: Dict[str, int] = {}
            for n in filtered:
                lbl = n.get("_label", "")
                groups2[lbl] = groups2.get(lbl, 0) + 1
            return _Result(
                [_Record({"label": k, "count": v}) for k, v in groups2.items()]
            )

        return _Result([])

    # ── Traverse ────────────────────────────────────────────────

    def _handle_traverse(self, q: str, params: Dict[str, Any]) -> _Result:
        props = self._parse_match_props(q, params)

        if "target_id" in q or "target_name" in q:
            anchors = [
                n
                for n in self._g._nodes.values()
                if all(n.get(k) == v for k, v in props.items())
            ]
            results = []
            for anchor in anchors:
                aid = anchor.get("node_id")
                for rel in self._g._rels:
                    if rel["_from"] == aid:
                        target = self._g._nodes.get(rel["_to"], {})
                        results.append(
                            _Record(
                                {
                                    "rel_type": rel["_type"],
                                    "target_id": target.get("node_id", ""),
                                    "target_name": target.get("name", ""),
                                    "target_label": target.get("_label", ""),
                                }
                            )
                        )
            return _Result(results)

        if "source_id" in q or "source_name" in q:
            anchors = [
                n
                for n in self._g._nodes.values()
                if all(n.get(k) == v for k, v in props.items())
            ]
            results = []
            for anchor in anchors:
                aid = anchor.get("node_id")
                for rel in self._g._rels:
                    if rel["_to"] == aid:
                        source = self._g._nodes.get(rel["_from"], {})
                        results.append(
                            _Record(
                                {
                                    "rel_type": rel["_type"],
                                    "source_id": source.get("node_id", ""),
                                    "source_name": source.get("name", ""),
                                    "source_label": source.get("_label", ""),
                                }
                            )
                        )
            return _Result(results)

        results = []
        for rel in self._g._rels:
            from_n = self._g._nodes.get(rel["_from"], {})
            to_n = self._g._nodes.get(rel["_to"], {})
            if all(from_n.get(k) == v for k, v in props.items()) and all(
                to_n.get(k) == v for k, v in props.items()
            ):
                results.append(
                    _Record(
                        {
                            "type": rel["_type"],
                            "from_id": from_n.get("node_id", ""),
                            "from_name": from_n.get("name", ""),
                            "to_id": to_n.get("node_id", ""),
                            "to_name": to_n.get("name", ""),
                        }
                    )
                )
        return _Result(results)

    # ── Lookup ──────────────────────────────────────────────────

    def _handle_lookup(self, q: str, params: Dict[str, Any]) -> _Result:
        props = self._parse_match_props(q, params)

        filtered = [
            n
            for n in self._g._nodes.values()
            if all(n.get(k) == v for k, v in props.items())
        ]

        return_clause = q.split("RETURN", 1)[1] if "RETURN" in q else ""
        first_col = return_clause.split("ORDER")[0].split("LIMIT")[0].strip()

        if first_col == "n" and " AS " not in first_col:
            return _Result([_Record({"n": n}) for n in filtered])

        return _Result([_Record(n) for n in filtered])

    # ── Utilities ───────────────────────────────────────────────

    def _parse_match_props(
        self, q: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        props: Dict[str, Any] = {}
        for m in re.finditer(
            r"MATCH\s+\(\w+(?:\:\w+)?\s*\{([^}]+)\}", q
        ):
            content = m.group(1)
            for pair in content.split(","):
                pair = pair.strip()
                if ":" in pair:
                    k, v = pair.split(":", 1)
                    k, v = k.strip(), v.strip()
                    if v.startswith("$"):
                        props[k] = params.get(v[1:])
        return props
