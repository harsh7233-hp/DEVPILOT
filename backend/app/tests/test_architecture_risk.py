from unittest.mock import patch

from app.services.architecture_risk import compute_architecture_risk


@patch("app.services.architecture_risk.get_all_relationships")
@patch("app.services.architecture_risk.get_all_nodes")
def test_hotspot_keeps_node_label(mock_nodes, mock_rels):
    mock_nodes.return_value = [
        {
            "node_id": "r:Function:src/a.py:core",
            "name": "core",
            "label": "Function",
            "file_path": "src/a.py",
            "start_line": 1,
            "end_line": 20,
        },
        {
            "node_id": "r:File:src/a.py",
            "name": "a.py",
            "label": "File",
            "file_path": "src/a.py",
        },
    ]
    mock_rels.return_value = [
        {
            "type": "CALLS",
            "from_id": f"r:Function:src/b.py:f{i}",
            "from_name": f"f{i}",
            "to_id": "r:Function:src/a.py:core",
            "to_name": "core",
        }
        for i in range(10)
    ]

    result = compute_architecture_risk("r")

    assert result["has_graph"] is True
    core = next(h for h in result["hotspots"] if h["node_id"] == "r:Function:src/a.py:core")
    assert core["label"] == "Function"
    assert core["metrics"]["fan_in"] == 10
    assert core["risk"] == "high"
