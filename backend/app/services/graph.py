from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Dict, Generator, List, Optional

from neo4j import GraphDatabase, Session

from app.config import settings

_driver = None


def _get_driver():
    global _driver
    if _driver is None:
        if not settings.neo4j_password:
            from app.services.graph_memory import InMemoryGraph

            _driver = InMemoryGraph()
        else:
            _driver = GraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password),
            )
    return _driver


@contextmanager
def get_session() -> Generator[Optional[Session], None, None]:
    driver = _get_driver()
    if driver is None:
        yield None
        return
    session = driver.session()
    try:
        yield session
    finally:
        session.close()


def close_driver():
    global _driver
    if _driver:
        _driver.close()
        _driver = None


def _run(session: Session, query: str, **params: Any) -> List[Dict[str, Any]]:
    result = session.run(query, **params)
    return [dict(record) for record in result]


def _run_one(session: Session, query: str, **params: Any) -> Optional[Dict[str, Any]]:
    results = _run(session, query, **params)
    return results[0] if results else None


# ── Schema ─────────────────────────────────────────────────────────


def ensure_schema(session: Session) -> None:
    constraints = [
        "CREATE CONSTRAINT IF NOT EXISTS FOR (r:Repository) REQUIRE r.repo_id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (f:File) REQUIRE f.node_id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Class) REQUIRE c.node_id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (fn:Function) REQUIRE fn.node_id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (m:Method) REQUIRE m.node_id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (a:ApiRoute) REQUIRE a.node_id IS UNIQUE",
    ]
    indexes = [
        "CREATE INDEX IF NOT EXISTS FOR (f:File) ON (f.repo_id)",
        "CREATE INDEX IF NOT EXISTS FOR (c:Class) ON (c.repo_id)",
        "CREATE INDEX IF NOT EXISTS FOR (fn:Function) ON (fn.repo_id)",
        "CREATE INDEX IF NOT EXISTS FOR (m:Method) ON (m.repo_id)",
        "CREATE INDEX IF NOT EXISTS FOR (a:ApiRoute) ON (a.repo_id)",
    ]
    for q in constraints + indexes:
        session.run(q)


# ── Node creation helpers ──────────────────────────────────────────


def _make_node_id(repo_id: str, label: str, name: str, file_path: str = "") -> str:
    return f"{repo_id}:{label}:{file_path}:{name}"


def upsert_repository(session: Session, repo_id: str, owner: str, name: str) -> None:
    node_id = f"Repository:{repo_id}"
    session.run(
        """
        MERGE (r:Repository {repo_id: $repo_id})
        SET r.node_id = $node_id, r.owner = $owner, r.name = $name
        """,
        repo_id=repo_id,
        node_id=node_id,
        owner=owner,
        name=name,
    )


def upsert_file(
    session: Session,
    repo_id: str,
    file_path: str,
    language: str = "",
    size: int = 0,
) -> str:
    node_id = _make_node_id(repo_id, "File", file_path)
    session.run(
        """
        MERGE (f:File {node_id: $node_id})
        SET f.repo_id = $repo_id, f.path = $path, f.language = $language, f.size = $size
        """,
        node_id=node_id,
        repo_id=repo_id,
        path=file_path,
        language=language,
        size=size,
    )
    return node_id


def upsert_function(
    session: Session,
    repo_id: str,
    name: str,
    file_path: str,
    start_line: int = 0,
    end_line: int = 0,
    is_async: bool = False,
    is_exported: bool = False,
) -> str:
    node_id = _make_node_id(repo_id, "Function", name, file_path)
    session.run(
        """
        MERGE (fn:Function {node_id: $node_id})
        SET fn.repo_id = $repo_id, fn.name = $name, fn.file_path = $file_path,
            fn.start_line = $start_line, fn.end_line = $end_line,
            fn.is_async = $is_async, fn.is_exported = $is_exported
        """,
        node_id=node_id,
        repo_id=repo_id,
        name=name,
        file_path=file_path,
        start_line=start_line,
        end_line=end_line,
        is_async=is_async,
        is_exported=is_exported,
    )
    return node_id


def upsert_class(
    session: Session,
    repo_id: str,
    name: str,
    file_path: str,
    start_line: int = 0,
    end_line: int = 0,
    extends: Optional[str] = None,
    is_exported: bool = False,
) -> str:
    node_id = _make_node_id(repo_id, "Class", name, file_path)
    session.run(
        """
        MERGE (c:Class {node_id: $node_id})
        SET c.repo_id = $repo_id, c.name = $name, c.file_path = $file_path,
            c.start_line = $start_line, c.end_line = $end_line,
            c.extends = $extends, c.is_exported = $is_exported
        """,
        node_id=node_id,
        repo_id=repo_id,
        name=name,
        file_path=file_path,
        start_line=start_line,
        end_line=end_line,
        extends=extends,
        is_exported=is_exported,
    )
    return node_id


def upsert_method(
    session: Session,
    repo_id: str,
    name: str,
    class_name: str,
    file_path: str,
    start_line: int = 0,
    end_line: int = 0,
    is_async: bool = False,
) -> str:
    node_id = _make_node_id(repo_id, "Method", f"{class_name}.{name}", file_path)
    session.run(
        """
        MERGE (m:Method {node_id: $node_id})
        SET m.repo_id = $repo_id, m.name = $name, m.class_name = $class_name,
            m.file_path = $file_path, m.start_line = $start_line,
            m.end_line = $end_line, m.is_async = $is_async
        """,
        node_id=node_id,
        repo_id=repo_id,
        name=name,
        class_name=class_name,
        file_path=file_path,
        start_line=start_line,
        end_line=end_line,
        is_async=is_async,
    )
    return node_id


def upsert_api_route(
    session: Session,
    repo_id: str,
    path: str,
    method: str,
    file_path: str,
    start_line: int = 0,
    end_line: int = 0,
) -> str:
    node_id = _make_node_id(repo_id, "ApiRoute", f"{method}:{path}", file_path)
    session.run(
        """
        MERGE (a:ApiRoute {node_id: $node_id})
        SET a.repo_id = $repo_id, a.path = $path, a.method = $method,
            a.file_path = $file_path, a.start_line = $start_line, a.end_line = $end_line
        """,
        node_id=node_id,
        repo_id=repo_id,
        path=path,
        method=method,
        file_path=file_path,
        start_line=start_line,
        end_line=end_line,
    )
    return node_id


# ── Relationship creation ──────────────────────────────────────────


def _merge_rel(
    session: Session,
    from_id: str,
    to_id: str,
    rel_type: str,
    props: Optional[Dict[str, Any]] = None,
) -> None:
    prop_str = ""
    if props:
        prop_pairs = ", ".join(f"{k}: ${k}" for k in props)
        prop_str = " {" + prop_pairs + "}"
    query = f"""
        MATCH (a {{node_id: $from_id}})
        MATCH (b {{node_id: $to_id}})
        MERGE (a)-[r:{rel_type}{prop_str}]->(b)
    """
    params: Dict[str, Any] = {"from_id": from_id, "to_id": to_id}
    if props:
        params.update(props)
    session.run(query, **params)


def _make_imports_rel(
    session: Session,
    from_file: str,
    to_file: str,
    source: str,
    names: Optional[List[str]] = None,
) -> None:
    _merge_rel(session, from_file, to_file, "IMPORTS", {"source": source})


def _make_calls_rel(
    session: Session,
    caller_id: str,
    callee_id: str,
) -> None:
    _merge_rel(session, caller_id, callee_id, "CALLS")


def _make_extends_rel(
    session: Session,
    child_id: str,
    parent_id: str,
) -> None:
    _merge_rel(session, child_id, parent_id, "EXTENDS")


def _make_implements_rel(
    session: Session,
    class_id: str,
    interface_id: str,
) -> None:
    _merge_rel(session, class_id, interface_id, "IMPLEMENTS")


def _make_uses_rel(
    session: Session,
    from_id: str,
    to_id: str,
    usage_type: str = "reference",
) -> None:
    _merge_rel(session, from_id, to_id, "USES", {"usage_type": usage_type})


def _make_depends_on_rel(
    session: Session,
    from_id: str,
    to_id: str,
) -> None:
    _merge_rel(session, from_id, to_id, "DEPENDS_ON")


# ── Graph build from parsed files ──────────────────────────────────


def build_graph_from_parsed(
    repo_id: str,
    owner: str,
    name: str,
    parsed_files: List[Dict[str, Any]],
    all_files: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    with get_session() as session:
        if session is None:
            return {"status": "error", "message": "Neo4j not configured"}

        ensure_schema(session)
        upsert_repository(session, repo_id, owner, name)

        file_node_ids: Dict[str, str] = {}
        function_node_ids: Dict[str, str] = {}
        class_node_ids: Dict[str, str] = {}
        method_node_ids: Dict[str, str] = {}
        stats = {
            "files": 0,
            "functions": 0,
            "classes": 0,
            "methods": 0,
            "imports": 0,
            "calls": 0,
            "extends": 0,
            "relationships": 0,
        }

        if all_files:
            for f in all_files:
                fp = f.get("path", "")
                lang = f.get("language", "")
                if fp:
                    file_node_ids[fp] = upsert_file(
                        session, repo_id, fp, lang, f.get("size", 0)
                    )
                    stats["files"] += 1
                    repo_file = f"Repository:{repo_id}"
                    _merge_rel(session, repo_file, file_node_ids[fp], "CONTAINS")
                    stats["relationships"] += 1

        for pf in parsed_files:
            fp = pf.get("file_path", "")
            lang = pf.get("language", "")
            if fp and fp not in file_node_ids:
                file_node_ids[fp] = upsert_file(session, repo_id, fp, lang)
                stats["files"] += 1
                repo_file = f"Repository:{repo_id}"
                _merge_rel(session, repo_file, file_node_ids[fp], "CONTAINS")

            for func in pf.get("functions", []):
                fid = upsert_function(
                    session,
                    repo_id,
                    func["name"],
                    fp,
                    func.get("start_line", 0),
                    func.get("end_line", 0),
                    func.get("is_async", False),
                    func.get("is_exported", False),
                )
                function_node_ids[f"{fp}:{func['name']}"] = fid
                _merge_rel(session, file_node_ids[fp], fid, "DEFINES")
                stats["functions"] += 1

            for cls in pf.get("classes", []):
                cid = upsert_class(
                    session,
                    repo_id,
                    cls["name"],
                    fp,
                    cls.get("start_line", 0),
                    cls.get("end_line", 0),
                    cls.get("extends"),
                    cls.get("is_exported", False),
                )
                class_node_ids[f"{fp}:{cls['name']}"] = cid
                _merge_rel(session, file_node_ids[fp], cid, "DEFINES")
                stats["classes"] += 1

                if cls.get("extends"):
                    parent_cid = class_node_ids.get(f"{fp}:{cls['extends']}")
                    if not parent_cid:
                        for key, cid_val in class_node_ids.items():
                            if key.endswith(f":{cls['extends']}"):
                                parent_cid = cid_val
                                break
                    if parent_cid:
                        _make_extends_rel(session, cid, parent_cid)
                        stats["extends"] += 1
                        stats["relationships"] += 1

                for iface in cls.get("implements", []):
                    iid = class_node_ids.get(f"{fp}:{iface}")
                    if not iid:
                        for key, cid_val in class_node_ids.items():
                            if key.endswith(f":{iface}"):
                                iid = cid_val
                                break
                    if iid:
                        _make_implements_rel(session, cid, iid)
                        stats["relationships"] += 1

            for method in pf.get("methods", []):
                mid = upsert_method(
                    session,
                    repo_id,
                    method["name"],
                    method.get("class_name", ""),
                    fp,
                    method.get("start_line", 0),
                    method.get("end_line", 0),
                    method.get("is_async", False),
                )
                method_node_ids[f"{fp}:{method.get('class_name', '')}.{method['name']}"] = mid
                parent_cid = class_node_ids.get(f"{fp}:{method.get('class_name', '')}")
                if parent_cid:
                    _merge_rel(session, parent_cid, mid, "HAS_METHOD")
                stats["methods"] += 1

        for pf in parsed_files:
            fp = pf.get("file_path", "")
            source_file_id = file_node_ids.get(fp)
            if not source_file_id:
                continue

            for imp in pf.get("imports", []):
                src = imp.get("source", "")
                target_file_id = file_node_ids.get(src)
                if target_file_id:
                    _make_imports_rel(session, source_file_id, target_file_id, src)
                    stats["imports"] += 1
                    stats["relationships"] += 1

            for call in pf.get("calls", []):
                call_name = call.get("name", "")
                callee_id = function_node_ids.get(f"{fp}:{call_name}")
                if not callee_id:
                    callee_id = method_node_ids.get(f"{fp}:*.{call_name}")
                if not callee_id:
                    for key, fid in function_node_ids.items():
                        if key.endswith(f":{call_name}"):
                            callee_id = fid
                            break
                if callee_id and callee_id != source_file_id:
                    _make_calls_rel(session, source_file_id, callee_id)
                    stats["calls"] += 1
                    stats["relationships"] += 1

        return {"status": "ok", "repo_id": repo_id, "stats": stats}


# ── Query helpers ──────────────────────────────────────────────────


def get_graph_summary(repo_id: str) -> Optional[Dict[str, Any]]:
    with get_session() as session:
        if session is None:
            return None
        result = _run_one(
            session,
            """
            MATCH (n {repo_id: $repo_id})
            RETURN labels(n)[0] AS label, count(n) AS count
            ORDER BY label
            """,
            repo_id=repo_id,
        )
        if not result:
            result = _run_one(
                session,
                "MATCH (r:Repository {repo_id: $repo_id}) RETURN r.repo_id AS id",
                repo_id=repo_id,
            )
            if not result:
                return None

        node_counts = _run(
            session,
            """
            MATCH (n {repo_id: $repo_id})
            RETURN labels(n)[0] AS label, count(n) AS count
            ORDER BY label
            """,
            repo_id=repo_id,
        )
        rel_counts = _run(
            session,
            """
            MATCH (a {repo_id: $repo_id})-[r]->(b {repo_id: $repo_id})
            RETURN type(r) AS rel_type, count(r) AS count
            ORDER BY rel_type
            """,
            repo_id=repo_id,
        )
        repo = _run_one(
            session,
            "MATCH (r:Repository {repo_id: $repo_id}) RETURN r.owner AS owner, r.name AS name",
            repo_id=repo_id,
        )
        return {
            "repo_id": repo_id,
            "owner": repo["owner"] if repo else "",
            "name": repo["name"] if repo else "",
            "nodes": {r["label"]: r["count"] for r in node_counts},
            "relationships": {r["rel_type"]: r["count"] for r in rel_counts},
        }


def get_node_detail(repo_id: str, node_id: str) -> Optional[Dict[str, Any]]:
    with get_session() as session:
        if session is None:
            return None
        node = _run_one(
            session,
            "MATCH (n {node_id: $node_id, repo_id: $repo_id}) RETURN n",
            node_id=node_id,
            repo_id=repo_id,
        )
        if not node:
            return None
        n = dict(node["n"])

        outgoing = _run(
            session,
            """
            MATCH (n {node_id: $node_id, repo_id: $repo_id})-[r]->(m)
            RETURN type(r) AS rel_type, m.node_id AS target_id, m.name AS target_name,
                   labels(m)[0] AS target_label
            """,
            node_id=node_id,
            repo_id=repo_id,
        )
        incoming = _run(
            session,
            """
            MATCH (m)-[r]->(n {node_id: $node_id, repo_id: $repo_id})
            RETURN type(r) AS rel_type, m.node_id AS source_id, m.name AS source_name,
                   labels(m)[0] AS source_label
            """,
            node_id=node_id,
            repo_id=repo_id,
        )
        return {
            "node": n,
            "outgoing": outgoing,
            "incoming": incoming,
        }


def get_all_nodes(repo_id: str, label: Optional[str] = None) -> List[Dict[str, Any]]:
    with get_session() as session:
        if session is None:
            return []
        if label:
            return _run(
                session,
                f"MATCH (n:{label} {{repo_id: $repo_id}}) RETURN n ORDER BY n.name",
                repo_id=repo_id,
            )
        return _run(
            session,
            "MATCH (n {repo_id: $repo_id}) RETURN n ORDER BY labels(n)[0], n.name",
            repo_id=repo_id,
        )


def get_all_relationships(repo_id: str) -> List[Dict[str, Any]]:
    with get_session() as session:
        if session is None:
            return []
        return _run(
            session,
            """
            MATCH (a {repo_id: $repo_id})-[r]->(b {repo_id: $repo_id})
            RETURN type(r) AS type, a.node_id AS from_id, a.name AS from_name,
                   b.node_id AS to_id, b.name AS to_name
            """,
            repo_id=repo_id,
        )


def delete_graph(repo_id: str) -> bool:
    with get_session() as session:
        if session is None:
            return False
        session.run(
            "MATCH (n {repo_id: $repo_id}) DETACH DELETE n",
            repo_id=repo_id,
        )
        return True
