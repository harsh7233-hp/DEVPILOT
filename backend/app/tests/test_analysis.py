from app.services.analysis import (
    AnalysisJob,
    detect_language,
    filter_files,
    should_ignore_path,
)


def test_should_ignore_node_modules():
    assert should_ignore_path("node_modules/package/index.js") is True


def test_should_ignore_git_dir():
    assert should_ignore_path(".git/config") is True


def test_should_ignore_pycache():
    assert should_ignore_path("src/__pycache__/module.pyc") is True


def test_should_ignore_lock_files():
    assert should_ignore_path("package-lock.json") is True
    assert should_ignore_path("yarn.lock") is True


def test_should_ignore_dotenv():
    assert should_ignore_path(".env") is True
    assert should_ignore_path(".env.local") is True
    assert should_ignore_path(".env.production") is True


def test_should_not_ignore_source_files():
    assert should_ignore_path("src/index.ts") is False
    assert should_ignore_path("app/main.py") is False
    assert should_ignore_path("lib/utils.js") is False


def test_should_not_ignore_env_example():
    assert should_ignore_path(".env.example") is False


def test_should_not_ignore_gitignore():
    assert should_ignore_path(".gitignore") is False


def test_filter_files_removes_directories():
    tree = [
        {"path": "src/index.ts", "type": "blob", "size": 100, "sha": "abc"},
        {"path": "src", "type": "tree", "size": 0, "sha": "def"},
    ]
    result = filter_files(tree)
    assert len(result) == 1
    assert result[0]["path"] == "src/index.ts"


def test_filter_files_removes_ignored_dirs():
    tree = [
        {"path": "src/index.ts", "type": "blob", "size": 100, "sha": "abc"},
        {"path": "node_modules/pkg/index.js", "type": "blob", "size": 50, "sha": "def"},
        {"path": "dist/bundle.js", "type": "blob", "size": 200, "sha": "ghi"},
    ]
    result = filter_files(tree)
    assert len(result) == 1
    assert result[0]["path"] == "src/index.ts"


def test_filter_files_removes_large_files():
    tree = [
        {"path": "src/small.ts", "type": "blob", "size": 100, "sha": "abc"},
        {"path": "data/large.json", "type": "blob", "size": 2_000_000, "sha": "def"},
    ]
    result = filter_files(tree)
    assert len(result) == 1
    assert result[0]["path"] == "src/small.ts"


def test_filter_files_removes_lock_files():
    tree = [
        {"path": "src/index.ts", "type": "blob", "size": 100, "sha": "abc"},
        {"path": "package-lock.json", "type": "blob", "size": 5000, "sha": "def"},
    ]
    result = filter_files(tree)
    assert len(result) == 1


def test_detect_language_typescript():
    assert detect_language("src/index.ts") == "TypeScript"
    assert detect_language("src/App.tsx") == "TypeScript"


def test_detect_language_javascript():
    assert detect_language("src/utils.js") == "JavaScript"
    assert detect_language("src/App.jsx") == "JavaScript"


def test_detect_language_python():
    assert detect_language("app/main.py") == "Python"


def test_detect_language_dockerfile():
    assert detect_language("Dockerfile") == "Dockerfile"


def test_detect_language_unknown():
    assert detect_language("README.xyz") == "Unknown"


def test_analysis_job_creation():
    job = AnalysisJob("owner", "repo", "main")
    assert job.owner == "owner"
    assert job.repo == "repo"
    assert job.branch == "main"
    assert job.status == "pending"
    assert job.progress == 0.0


def test_analysis_job_to_dict():
    job = AnalysisJob("owner", "repo", "main")
    d = job.to_dict()
    assert d["owner"] == "owner"
    assert d["status"] == "pending"
    assert "id" in d
    assert d["files"] == []
