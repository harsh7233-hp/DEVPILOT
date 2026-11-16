from neo4j.exceptions import ServiceUnavailable

from app.services import graph


def test_build_graph_falls_back_to_memory_when_neo4j_is_unavailable(monkeypatch):
    calls = {"count": 0}
    memory_used = {"value": False}

    def fake_build(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise ServiceUnavailable("Neo4j is down")
        return {"status": "ok", "repo_id": "repo-id", "stats": {}}

    def fake_use_memory():
        memory_used["value"] = True

    monkeypatch.setattr(graph, "_build_graph_from_parsed_with_store", fake_build)
    monkeypatch.setattr(graph, "_use_memory_graph", fake_use_memory)
    monkeypatch.setattr(graph.settings, "neo4j_password", "dummy")

    result = graph.build_graph_from_parsed("repo-id", "owner", "repo", [], [])

    assert result["status"] == "ok"
    assert calls["count"] == 2
    assert memory_used["value"] is True


def test_build_graph_does_not_fall_back_without_neo4j(monkeypatch):
    def fake_build(*args, **kwargs):
        raise ServiceUnavailable("Neo4j is down")

    monkeypatch.setattr(graph, "_build_graph_from_parsed_with_store", fake_build)
    monkeypatch.setattr(graph.settings, "neo4j_password", "")

    try:
        graph.build_graph_from_parsed("repo-id", "owner", "repo", [], [])
    except ServiceUnavailable:
        pass
    else:
        raise AssertionError("expected ServiceUnavailable to propagate")
