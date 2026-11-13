import pytest
from unittest.mock import patch

from app.api.analysis import _run_analysis
from app.services.analysis import AnalysisJob, _jobs
from app.services.github import GitHubAPIError


@pytest.fixture(autouse=True)
def clean_jobs():
    _jobs.clear()
    yield
    _jobs.clear()


def _job() -> AnalysisJob:
    job = AnalysisJob("owner", "repo", "main")
    _jobs[job.id] = job
    return job


def _tree(path: str = "src/A.java") -> list:
    return [{"path": path, "type": "blob", "size": 60, "sha": "x"}]


@pytest.mark.asyncio
@patch("app.api.analysis.save_job")
@patch("app.api.analysis.get_file_tree_checked")
async def test_analysis_fails_on_github_auth_error(mock_tree, _save):
    job = _job()
    mock_tree.side_effect = GitHubAPIError(403, "API rate limit exceeded")

    await _run_analysis(job.id, "tok")

    assert job.status == "failed"
    assert "denied access" in (job.error or "").lower()


@pytest.mark.asyncio
@patch("app.api.analysis.save_job")
@patch("app.api.analysis.get_file_tree_checked", return_value=[])
async def test_analysis_fails_on_empty_tree(mock_tree, _save):
    job = _job()

    await _run_analysis(job.id, "tok")

    assert job.status == "failed"
    assert "empty" in (job.error or "").lower() or "no files" in (job.error or "").lower()


@pytest.mark.asyncio
@patch("app.api.analysis.save_job")
@patch("app.api.analysis.get_repo_tarball", return_value={})
@patch("app.api.analysis.get_file_content", return_value=None)
@patch("app.api.analysis.get_file_tree_checked")
async def test_analysis_fails_when_source_files_unreadable(
    mock_tree, mock_content, mock_tarball, _save
):
    job = _job()
    mock_tree.return_value = _tree()

    await _run_analysis(job.id, "tok")

    assert job.status == "failed"
    assert "could not read" in (job.error or "").lower()


@pytest.mark.asyncio
@patch("app.api.analysis.save_job")
@patch("app.api.analysis.get_repo_tarball", return_value={})
@patch(
    "app.api.analysis.get_file_content",
    return_value="public class A { int add(int a, int b) { return a + b; } }",
)
@patch("app.api.analysis.get_file_tree_checked")
async def test_analysis_completes_with_per_file_fallback(
    mock_tree, mock_content, mock_tarball, _save
):
    job = _job()
    mock_tree.return_value = _tree()

    await _run_analysis(job.id, "tok")

    assert job.status == "completed"
    assert job.parsed_files
    assert job.parsed_files[0]["file_path"] == "src/A.java"
    assert job.parsed_files[0]["language"] == "java"


@pytest.mark.asyncio
@patch("app.api.analysis.save_job")
@patch("app.api.analysis.get_file_content")
@patch(
    "app.api.analysis.get_repo_tarball",
    return_value={"src/A.java": "public class A { int add(int a, int b) { return a + b; } }"},
)
@patch("app.api.analysis.get_file_tree_checked")
async def test_analysis_uses_tarball_contents(
    mock_tree, mock_tarball, mock_content, _save
):
    job = _job()
    mock_tree.return_value = _tree()

    await _run_analysis(job.id, "tok")

    assert job.status == "completed"
    assert job.parsed_files[0]["file_path"] == "src/A.java"
    mock_content.assert_not_called()
