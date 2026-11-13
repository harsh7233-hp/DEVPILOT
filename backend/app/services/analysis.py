from __future__ import annotations

import json
import os
import time
import uuid
from typing import Any, Dict, List, Optional

_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
_JOBS_FILE = os.path.join(_DATA_DIR, "jobs.json")

# Source file extensions we care about
SOURCE_EXTENSIONS = {
    ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs",
    ".py", ".pyi",
    ".java", ".kt", ".scala",
    ".go",
    ".rs",
    ".rb",
    ".php",
    ".cs",
    ".swift",
    ".c", ".cpp", ".h", ".hpp",
    ".css", ".scss", ".less",
    ".html", ".htm",
    ".json", ".yaml", ".yml", ".toml",
    ".md", ".mdx",
    ".sql",
    ".sh", ".bash",
    ".env.example",
    ".gitignore", ".dockerignore",
    "Dockerfile", "docker-compose.yml",
    "Makefile", "CMakeLists.txt",
    "package.json", "tsconfig.json",
    "pyproject.toml", "setup.py", "setup.cfg",
    "Cargo.toml", "go.mod",
}

IGNORED_DIRS = {
    "node_modules", ".git", ".next", ".nuxt", "dist", "build", "out",
    "__pycache__", ".pytest_cache", ".venv", "venv", "env",
    ".idea", ".vscode", ".cache", ".turbo",
    "coverage", ".nyc_output",
    "vendor", "target",
    ".terraform", ".serverless",
    "tmp", "temp",
}

IGNORED_FILES = {
    ".DS_Store", "Thumbs.db", "desktop.ini",
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "poetry.lock", "Pipfile.lock",
    "composer.lock", "Gemfile.lock",
    "Cargo.lock",
    ".env", ".env.local", ".env.*.local",
    "*.min.js", "*.min.css",
    "*.map",
}

MAX_FILE_SIZE = 1_000_000  # 1MB


class AnalysisJob:
    def __init__(
        self,
        owner: str,
        repo: str,
        branch: str,
    ) -> None:
        self.id: str = str(uuid.uuid4())
        self.created_at: float = time.time()
        self.owner: str = owner
        self.repo: str = repo
        self.branch: str = branch
        self.status: str = "pending"
        self.progress: float = 0.0
        self.message: str = "Job created"
        self.files: List[Dict[str, Any]] = []
        self.parsed_files: List[Dict[str, Any]] = []
        self.total_files: int = 0
        self.filtered_files: int = 0
        self.error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "created_at": self.created_at,
            "owner": self.owner,
            "repo": self.repo,
            "branch": self.branch,
            "status": self.status,
            "progress": self.progress,
            "message": self.message,
            "total_files": self.total_files,
            "filtered_files": self.filtered_files,
            "files": self.files,
            "parsed_files": self.parsed_files,
            "error": self.error,
        }


_jobs: Dict[str, AnalysisJob] = {}


def _save_jobs() -> None:
    try:
        os.makedirs(_DATA_DIR, exist_ok=True)
        data = {jid: job.to_dict() for jid, job in _jobs.items()}
        with open(_JOBS_FILE, "w") as f:
            json.dump(data, f)
    except Exception:
        pass


def _load_jobs() -> None:
    if not os.path.exists(_JOBS_FILE):
        return
    try:
        with open(_JOBS_FILE) as f:
            data = json.load(f)
        for jid, d in data.items():
            job = AnalysisJob(d["owner"], d["repo"], d["branch"])
            job.id = d["id"]
            job.created_at = d.get("created_at", 0)
            job.status = d["status"]
            job.progress = d.get("progress", 0)
            job.message = d.get("message", "")
            job.files = d.get("files", [])
            job.parsed_files = d.get("parsed_files", [])
            job.total_files = d.get("total_files", 0)
            job.filtered_files = d.get("filtered_files", 0)
            job.error = d.get("error")
            _jobs[jid] = job
    except Exception:
        pass


_load_jobs()


def create_job(owner: str, repo: str, branch: str) -> AnalysisJob:
    job = AnalysisJob(owner, repo, branch)
    _jobs[job.id] = job
    _save_jobs()
    return job


def get_job(job_id: str) -> Optional[AnalysisJob]:
    return _jobs.get(job_id)


def get_jobs_for_repo(owner: str, repo: str) -> List[AnalysisJob]:
    return [j for j in _jobs.values() if j.owner == owner and j.repo == repo]


def latest_job(jobs: List[AnalysisJob]) -> Optional[AnalysisJob]:
    """Return the most recently created job, preserving insertion order on ties."""
    if not jobs:
        return None
    return max(enumerate(jobs), key=lambda pair: (pair[1].created_at, pair[0]))[1]


def save_job(job: AnalysisJob) -> None:
    _save_jobs()


ALLOWED_DOTFILES = {".env.example", ".gitignore", ".dockerignore"}


def should_ignore_path(path: str) -> bool:
    parts = path.split("/")

    for part in parts:
        if part in IGNORED_DIRS:
            return True
        if part.startswith(".") and part not in ALLOWED_DOTFILES:
            return True

    filename = parts[-1] if parts else path
    if filename in IGNORED_FILES:
        return True

    return False


def filter_files(tree: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    result = []
    for item in tree:
        if item["type"] != "blob":
            continue
        if should_ignore_path(item["path"]):
            continue
        if item.get("size", 0) > MAX_FILE_SIZE:
            continue
        result.append(item)
    return result


def detect_language(path: str) -> str:
    ext_map = {
        ".ts": "TypeScript", ".tsx": "TypeScript",
        ".js": "JavaScript", ".jsx": "JavaScript",
        ".mjs": "JavaScript", ".cjs": "JavaScript",
        ".py": "Python", ".pyi": "Python",
        ".java": "Java", ".kt": "Kotlin", ".scala": "Scala",
        ".go": "Go",
        ".rs": "Rust",
        ".rb": "Ruby",
        ".php": "PHP",
        ".cs": "C#",
        ".swift": "Swift",
        ".c": "C", ".cpp": "C++", ".h": "C", ".hpp": "C++",
        ".css": "CSS", ".scss": "SCSS", ".less": "LESS",
        ".html": "HTML", ".htm": "HTML",
        ".json": "JSON",
        ".yaml": "YAML", ".yml": "YAML", ".toml": "TOML",
        ".md": "Markdown", ".mdx": "Markdown",
        ".sql": "SQL",
        ".sh": "Shell", ".bash": "Shell",
    }

    for ext, lang in ext_map.items():
        if path.endswith(ext):
            return lang

    filename = path.split("/")[-1] if "/" in path else path
    name_map = {
        "Dockerfile": "Dockerfile",
        "docker-compose.yml": "YAML",
        "Makefile": "Makefile",
        "package.json": "JSON",
        "tsconfig.json": "JSON",
        "pyproject.toml": "TOML",
        "setup.py": "Python",
        "Cargo.toml": "TOML",
        "go.mod": "Go",
    }
    return name_map.get(filename, "Unknown")
