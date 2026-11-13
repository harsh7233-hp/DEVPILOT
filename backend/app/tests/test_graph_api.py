from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.services.analysis import AnalysisJob, _jobs

client = TestClient(app)


def _make_job(owner: str, repo: str, created_at: float, marker: str, status: str = "completed") -> AnalysisJob:
    job = AnalysisJob(owner, repo, "main")
    job.status = status
    job.created_at = created_at
    job.parsed_files = [
        {
            "file_path": f"{marker}.py",
            "language": "python",
            "functions": [],
            "classes": [],
        }
    ]
    job.files = [{"path": f"{marker}.py", "language": "python"}]
    _jobs[job.id] = job
    return job


@patch("app.api.graph._get_token", return_value="tok")
@patch("app.api.graph.build_graph_from_parsed")
def test_build_graph_uses_newest_completed_job(mock_build, _tok):
    _jobs.clear()
    _make_job("owner", "repo", 1.0, "old")
    newest = _make_job("owner", "repo", 2.0, "new")
    mock_build.return_value = {"status": "ok"}

    r = client.post(
        "/api/repositories/owner/repo/graph/build", cookies={"dp_session": "x"}
    )

    assert r.status_code == 200
    args = mock_build.call_args.args
    assert args[3] == newest.parsed_files
    assert args[4] == newest.files
    _jobs.clear()


@patch("app.api.graph._get_token", return_value="tok")
@patch("app.api.graph.build_graph_from_parsed")
def test_build_graph_ignores_newer_incomplete_job(mock_build, _tok):
    _jobs.clear()
    completed = _make_job("owner", "repo", 1.0, "done")
    _make_job("owner", "repo", 2.0, "pending", status="processing")
    mock_build.return_value = {"status": "ok"}

    r = client.post(
        "/api/repositories/owner/repo/graph/build", cookies={"dp_session": "x"}
    )

    assert r.status_code == 200
    assert mock_build.call_args.args[3] == completed.parsed_files
    _jobs.clear()


@patch("app.api.graph._get_token", return_value="tok")
def test_build_graph_requires_completed_analysis(_tok):
    _jobs.clear()

    r = client.post(
        "/api/repositories/owner/repo/graph/build", cookies={"dp_session": "x"}
    )

    assert r.status_code == 400
    assert "No completed analysis" in r.json()["detail"]
    _jobs.clear()
