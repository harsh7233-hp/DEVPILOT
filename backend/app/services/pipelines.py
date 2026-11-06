"""CI/CD & deployment configuration detection.

Detects pipelines from the actual repository file tree (and, for GitHub
Actions / GitLab / CircleCI configs, from file contents). Nothing is
assumed — only detected files are reported.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

from app.services.github import get_file_content

# (platform, path predicate, needs_content)
_DETECTION_RULES: List[Dict[str, Any]] = [
    {"platform": "GitHub Actions", "match": lambda p: p.startswith(".github/workflows/") and p.endswith((".yml", ".yaml")), "content": True},
    {"platform": "Jenkins", "match": lambda p: p == "Jenkinsfile" or p == "Jenkinsfile.rb", "content": True},
    {"platform": "GitLab CI", "match": lambda p: p == ".gitlab-ci.yml", "content": True},
    {"platform": "CircleCI", "match": lambda p: p.startswith(".circleci/") and p.endswith(("config.yml", "config.yaml")), "content": True},
    {"platform": "Travis CI", "match": lambda p: p == ".travis.yml", "content": False},
    {"platform": "Docker", "match": lambda p: p.split("/")[-1] in ("Dockerfile",) or p.split("/")[-1].startswith("Dockerfile."), "content": False},
    {"platform": "Docker Compose", "match": lambda p: p.split("/")[-1] in ("docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"), "content": True},
    {"platform": "Kubernetes", "match": lambda p: any(seg in ("k8s", "kubernetes", "charts") for seg in p.split("/")) and p.endswith((".yml", ".yaml")) and not p.startswith(".github/"), "content": False},
    {"platform": "Terraform", "match": lambda p: p.endswith(".tf") and "__pycache__" not in p, "content": False},
]

_TRIGGER_KEYWORDS = {
    "push": "push", "pull_request": "pull request", "schedule": "schedule",
    "workflow_dispatch": "manual", "release": "release", "tag": "tag",
    "main": "branch main", "master": "branch master", "cron": "cron",
}

_CAPABILITY_KEYWORDS = {
    "build": ["build", "compile", "bundle", "package", "gradle build", "mvn ", "make build", "docker build"],
    "test": ["test", "pytest", "jest", "vitest", "rspec", "go test", "cargo test", "mvn test"],
    "lint": ["lint", "eslint", "ruff", "flake8", "pylint", "prettier", "golangci", "clippy", "checkstyle"],
    "security": ["security", "audit", "trivy", "snyk", "codeql", "bandit", "safety check", "npm audit", "pip-audit", "scan"],
    "deploy": ["deploy", "publish", "release", "upload-artifact", "push --tags", "kubectl apply", "terraform apply", "vercel", "netlify", "fly.io", "render.com"],
}


def _extract_yaml_top_keys(content: str, key: str) -> List[str]:
    """Extract list values under a top-level YAML `key:` block (minimal parser)."""
    values: List[str] = []
    lines = content.splitlines()
    in_block = False
    base_indent = 0
    key_re = re.compile(rf"^{key}:\s*(.*)$")
    for line in lines:
        if not line.strip() or line.strip().startswith("#"):
            continue
        m = key_re.match(line)
        if m:
            in_block = True
            base_indent = len(line) - len(line.lstrip())
            inline = m.group(1).strip()
            if inline.startswith("[") and inline.endswith("]"):
                values.extend(v.strip(" '\"") for v in inline[1:-1].split(",") if v.strip())
            continue
        if in_block:
            indent = len(line) - len(line.lstrip())
            if indent <= base_indent:
                in_block = False
                continue
            stripped = line.strip()
            if stripped.startswith("- ") or (stripped.endswith(":") and indent == base_indent + 2):
                val = stripped.lstrip("- ").rstrip(":").strip(" '\"")
                if val:
                    values.append(val)
    return values


def _extract_job_names(content: str) -> List[str]:
    """Job ids under GitHub Actions `jobs:` (two-space indented keys with runs-on/steps children)."""
    jobs: List[str] = []
    lines = content.splitlines()
    in_jobs = False
    jobs_indent = 0
    for line in lines:
        if line.strip().startswith("#"):
            continue
        if re.match(r"^jobs:\s*$", line):
            in_jobs = True
            jobs_indent = 0
            continue
        if in_jobs:
            if not line.strip():
                continue
            indent = len(line) - len(line.lstrip())
            if jobs_indent == 0:
                jobs_indent = indent
            if indent < jobs_indent:
                break
            m = re.match(r"^(\s*)([\w\-./]+):\s*$", line)
            if m and len(m.group(1)) == jobs_indent:
                jobs.append(m.group(2))
    return jobs


def _capabilities(text: str) -> Dict[str, bool]:
    low = text.lower()
    return {
        cap: any(kw in low for kw in kws)
        for cap, kws in _CAPABILITY_KEYWORDS.items()
    }


async def detect_pipelines(token: str, owner: str, repo: str,
                           tree: List[Dict[str, Any]], ref: str = "main") -> Dict[str, Any]:
    blobs = [t["path"] for t in tree if t.get("type") == "blob"]
    pipelines: List[Dict[str, Any]] = []

    content_rules = [r for r in _DETECTION_RULES if r["content"]]
    to_fetch: Dict[str, str] = {}  # path -> platform

    for rule in _DETECTION_RULES:
        matches = [p for p in blobs if rule["match"](p)]
        if not matches:
            continue
        platform = rule["platform"]
        if rule.get("content"):
            fetch_list = matches[:12]
            for p in fetch_list:
                to_fetch[p] = platform
        else:
            pipelines.append({
                "name": f"{platform} ({matches[0].split('/')[-1]})" if platform != "Kubernetes"
                        else f"Kubernetes manifests ({len(matches)} files)",
                "platform": platform,
                "files": matches[:10],
                "trigger": [],
                "jobs": [],
                "job_count": max(1, len(matches)) if platform in ("Docker", "Terraform", "Kubernetes") else 1,
                "capabilities": {"build": platform in ("Docker",), "test": False, "lint": False,
                                 "security": False, "deploy": platform == "Kubernetes"},
                "source": "static-analysis",
            })

    # fetch config contents
    fetched: Dict[str, Optional[str]] = {}
    import asyncio

    sem = asyncio.Semaphore(8)

    async def fetch(p: str) -> None:
        async with sem:
            try:
                fetched[p] = await get_file_content(token, owner, repo, p, ref)
            except Exception:
                fetched[p] = None

    await asyncio.gather(*(fetch(p) for p in to_fetch))

    # GitHub Actions workflows — one entry per workflow file
    gh_paths = [p for p, plat in to_fetch.items() if plat == "GitHub Actions"]
    for p in gh_paths:
        text = fetched.get(p) or ""
        triggers_raw = _extract_yaml_top_keys(text, "on")
        triggers: List[str] = []
        for t in triggers_raw:
            mapped = _TRIGGER_KEYWORDS.get(t.lower(), t)
            if mapped not in triggers:
                triggers.append(mapped)
        if not triggers and re.search(r"^on\s*:", text, re.MULTILINE):
            on_block = _extract_on_branches(text)
            triggers = on_block or ["push"]
        caps = _capabilities(text)
        name_match = re.search(r"^name:\s*(.+)$", text, re.MULTILINE)
        pipelines.append({
            "name": (name_match.group(1).strip("'\"") if name_match else p.split("/")[-1]),
            "platform": "GitHub Actions",
            "files": [p],
            "trigger": triggers,
            "jobs": _extract_job_names(text)[:20],
            "job_count": len(_extract_job_names(text)),
            "capabilities": caps,
            "source": "static-analysis",
        })

    # other single-file platforms
    for p, platform in to_fetch.items():
        if platform == "GitHub Actions":
            continue
        text = fetched.get(p) or ""
        triggers: List[str] = []
        if platform == "GitLab CI":
            rules_triggers = _extract_yaml_top_keys(text, "workflow")
            triggers = ["push"]  # gitlab default trigger
            if rules_triggers:
                triggers = ["push"]
            if "rules:" in text and "schedules" in text:
                triggers.append("schedule")
        elif platform == "CircleCI":
            triggers = ["push"]
        elif platform == "Jenkins":
            if "cron" in text or "trigger" in text.lower():
                triggers = ["trigger/cron"]
            else:
                triggers = ["webhook/push"]
        elif platform == "Docker Compose":
            triggers = []
        caps = _capabilities(text)
        pipelines.append({
            "name": p.split("/")[-1],
            "platform": platform,
            "files": [p],
            "trigger": triggers,
            "jobs": ([j for j in _extract_job_names(text)][:20] if platform in ("GitLab CI", "CircleCI") else []),
            "job_count": len(_extract_job_names(text)) if platform in ("GitLab CI", "CircleCI") else max(1, text.count("stage") if text else 0),
            "capabilities": caps,
            "source": "static-analysis",
        })

    order = ["GitHub Actions", "Jenkins", "GitLab CI", "CircleCI", "Travis CI",
             "Docker Compose", "Docker", "Kubernetes", "Terraform"]
    pipelines.sort(key=lambda x: (order.index(x["platform"]) if x["platform"] in order else 99, x["name"]))

    by_platform: Dict[str, int] = {}
    for p_ in pipelines:
        by_platform[p_["platform"]] = by_platform.get(p_["platform"], 0) + 1

    overall_caps = {cap: any(p_["capabilities"].get(cap) for p_ in pipelines)
                    for cap in _CAPABILITY_KEYWORDS}

    return {
        "total": len(pipelines),
        "by_platform": by_platform,
        "overall_capabilities": overall_caps,
        "pipelines": pipelines[:40],
        "note": "Only configurations actually present in the repository are listed.",
    }


def _extract_on_branches(text: str) -> List[str]:
    """Fallback minimal parse of `on: push / pull_request` short forms."""
    found: List[str] = []
    m = re.search(r"^on:\s*$\n((?:\s{2,}.*\n)+)", text, re.MULTILINE)
    if m:
        for line in m.group(1).splitlines():
            mm = re.match(r"^\s*-?\s*([A-Za-z_]+):?\s*$", line)
            if mm and mm.group(1) in _TRIGGER_KEYWORDS:
                found.append(_TRIGGER_KEYWORDS[mm.group(1)])
    else:
        m2 = re.search(r"^on:\s*\[(.+?)\]", text, re.MULTILINE)
        if m2:
            for t in m2.group(1).split(","):
                t = t.strip(" '\"")
                if t:
                    found.append(_TRIGGER_KEYWORDS.get(t.lower(), t))
    return found
