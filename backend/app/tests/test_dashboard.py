from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from app.main import app
from app.services.analysis import _jobs, AnalysisJob
from app.services.ai import _conversations


client = TestClient(app)

COOKIE = "dp_session=eyJ0b2tlbiI6InRlc3QxMjMifQ==;mHk4y2eK1k9W2O3jLbA4vTqNcR5xJ8mP"


def _clear():
    _jobs.clear()
    _conversations.clear()


def test_dashboard_unauthenticated():
    _clear()
    r = client.get("/api/dashboard")
    assert r.status_code == 401


@patch("app.api.dashboard._get_token", return_value="tok")
@patch("app.api.dashboard.get_repositories")
def test_dashboard_empty_repos(mock_repos, _tok):
    _clear()
    mock_repos.return_value = []
    r = client.get("/api/dashboard", cookies={"dp_session": "x"})
    assert r.status_code == 200
    data = r.json()
    assert data["summary"]["repositories"] == 0
    assert data["repositories"] == []


@patch("app.api.dashboard._get_token", return_value="tok")
@patch("app.api.dashboard.get_repositories")
def test_dashboard_with_repos(mock_repos, _tok):
    _clear()
    mock_repos.return_value = [
        {"name": "my-app", "owner": {"login": "testorg"}, "language": "TypeScript", "stars": 10, "description": "Test", "updated_at": "2024-01-01"},
    ]
    job = AnalysisJob("testorg", "my-app", "main")
    job.status = "completed"
    job.total_files = 50
    job.filtered_files = 40
    job.parsed_files = [
        {
            "file_path": "src/a.ts",
            "language": "TypeScript",
            "functions": [{"name": "f1"}, {"name": "f2"}],
            "classes": [{"name": "C1"}],
        },
        {"file_path": "src/b.ts", "language": "TypeScript", "functions": [{"name": "g1"}], "classes": []},
    ]
    _jobs[job.id] = job

    r = client.get("/api/dashboard", cookies={"dp_session": "x"})
    assert r.status_code == 200
    data = r.json()
    assert data["summary"]["repositories"] == 1
    assert data["summary"]["analyzed"] == 1
    assert data["summary"]["total_files"] == 40
    assert data["summary"]["total_functions"] == 3
    assert data["summary"]["total_classes"] == 1
    repo = data["repositories"][0]
    assert repo["owner"] == "testorg"
    assert repo["repo"] == "my-app"
    assert repo["status"] == "analyzed"
    assert repo["filtered_files"] == 40
    assert repo["functions"] == 3
    assert repo["classes"] == 1
    _clear()


@patch("app.api.dashboard._get_token", return_value="tok")
@patch("app.api.dashboard.get_repositories")
def test_dashboard_repos_pending(mock_repos, _tok):
    _clear()
    mock_repos.return_value = [
        {"name": "new-repo", "owner": {"login": "user1"}, "language": "Python", "stars": 0, "description": "", "updated_at": "2024-01-01"},
    ]
    r = client.get("/api/dashboard", cookies={"dp_session": "x"})
    assert r.status_code == 200
    data = r.json()
    repo = data["repositories"][0]
    assert repo["status"] == "pending"
    assert repo["filtered_files"] == 0
    _clear()


@patch("app.api.dashboard._get_token", return_value="tok")
@patch("app.api.dashboard.get_repositories")
def test_dashboard_with_ai_messages(mock_repos, _tok):
    _clear()
    mock_repos.return_value = [
        {"name": "chat-repo", "owner": {"login": "dev"}, "language": "Go", "stars": 5, "description": "", "updated_at": "2024-01-01"},
    ]
    _conversations[("dev", "chat-repo")] = [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
        {"role": "user", "content": "how?"},
    ]
    r = client.get("/api/dashboard", cookies={"dp_session": "x"})
    assert r.status_code == 200
    data = r.json()
    assert data["summary"]["ai_messages"] == 3
    assert data["repositories"][0]["ai_messages"] == 3
    _clear()


@patch("app.api.dashboard._get_token", return_value="tok")
@patch("app.api.dashboard.get_repositories")
def test_dashboard_repo_detail(mock_repos, _tok):
    _clear()
    mock_repos.return_value = []
    r = client.get("/api/dashboard/testorg/my-app", cookies={"dp_session": "x"})
    assert r.status_code == 200
    data = r.json()
    assert data["owner"] == "testorg"
    assert data["repo"] == "my-app"
    assert data["status"] == "pending"
    assert data["analysis_jobs"] == []
    _clear()
