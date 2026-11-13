from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Request

from app.services.ai import _conversations
from app.services.analysis import get_jobs_for_repo, latest_job
from app.services.graph import get_graph_summary
from app.services.session import SESSION_COOKIE, decode_session
from app.services.github import get_repositories, get_repository

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _get_token(request: Request) -> str:
    cookie = request.cookies.get(SESSION_COOKIE)
    if not cookie:
        raise HTTPException(status_code=401, detail="Not authenticated")
    session = decode_session(cookie)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return session["token"]


def _repo_id(owner: str, repo: str) -> str:
    raw = f"{owner}/{repo}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _get_repo_stats(owner: str, repo: str) -> Dict[str, Any]:
    """Get real stats for a single repository."""
    jobs = get_jobs_for_repo(owner, repo)
    completed = [j for j in jobs if j.status == "completed"]
    latest = latest_job(completed)

    # File and entity counts from latest analysis
    total_files = latest.total_files if latest else 0
    filtered_files = latest.filtered_files if latest else 0
    functions = 0
    classes = 0
    if latest and latest.parsed_files:
        for pf in latest.parsed_files:
            for fn in pf.get("functions", []):
                if not str(fn.get("name", "")).startswith("<"):
                    functions += 1
            classes += len(pf.get("classes", []))
            methods = pf.get("methods", [])
            functions += len(methods)

    # Graph stats
    rid = _repo_id(owner, repo)
    graph_summary = get_graph_summary(rid)
    nodes_count = 0
    rels_count = 0
    nodes_by_label = {}
    rels_by_type = {}
    has_graph = False
    if graph_summary:
        has_graph = True
        nodes_by_label = graph_summary.get("nodes", {})
        rels_by_type = graph_summary.get("relationships", {})
        nodes_count = sum(nodes_by_label.values())
        rels_count = sum(rels_by_type.values())

    # AI activity count
    ai_messages = 0
    for key in _conversations:
        if isinstance(key, tuple) and len(key) == 2 and key[0] == owner and key[1] == repo:
            ai_messages += len(_conversations[key])

    # Analysis job statuses
    analysis_statuses = []
    for j in jobs[-5:]:  # Last 5
        analysis_statuses.append({
            "id": j.id,
            "branch": j.branch,
            "status": j.status,
            "progress": j.progress,
            "message": j.message,
            "total_files": j.total_files,
            "filtered_files": j.filtered_files,
        })

    return {
        "owner": owner,
        "repo": repo,
        "status": "analyzed" if latest and latest.status == "completed" else "pending",
        "total_files": total_files,
        "filtered_files": filtered_files,
        "functions": functions,
        "classes": classes,
        "has_graph": has_graph,
        "nodes_count": nodes_count,
        "rels_count": rels_count,
        "nodes_by_label": nodes_by_label,
        "rels_by_type": rels_by_type,
        "ai_messages": ai_messages,
        "analysis_jobs": analysis_statuses,
        "latest_job_id": latest.id if latest else None,
    }


@router.get("")
async def get_dashboard(request: Request, search: str = ""):
    token = _get_token(request)

    if search and len(search) > 200:
        raise HTTPException(status_code=400, detail="Search query too long")

    try:
        repos = await get_repositories(token, search=search or None, page=1, per_page=50)
    except Exception:
        repos = []

    repo_stats = []
    total_files = 0
    total_functions = 0
    total_classes = 0
    total_nodes = 0
    total_rels = 0
    total_ai_messages = 0
    analyzed_count = 0

    for repo in repos:
        owner = repo.get("owner", {}).get("login", "")
        name = repo.get("name", "")
        if not owner or not name:
            continue

        stats = _get_repo_stats(owner, name)
        stats["language"] = repo.get("language", "")
        stats["stars"] = repo.get("stars", 0)
        stats["description"] = repo.get("description", "")
        stats["updated_at"] = repo.get("updated_at", "")
        repo_stats.append(stats)

        if stats["status"] == "analyzed":
            analyzed_count += 1
        total_files += stats["filtered_files"]
        total_functions += stats["functions"]
        total_classes += stats["classes"]
        total_nodes += stats["nodes_count"]
        total_rels += stats["rels_count"]
        total_ai_messages += stats["ai_messages"]

    return {
        "summary": {
            "repositories": len(repo_stats),
            "analyzed": analyzed_count,
            "total_files": total_files,
            "total_functions": total_functions,
            "total_classes": total_classes,
            "total_nodes": total_nodes,
            "total_relationships": total_rels,
            "ai_messages": total_ai_messages,
        },
        "repositories": repo_stats,
    }


@router.get("/{owner}/{repo}")
async def get_repo_dashboard(request: Request, owner: str, repo: str):
    token = _get_token(request)

    if not re.match(r'^[a-zA-Z0-9._-]+$', owner) or len(owner) > 100:
        raise HTTPException(status_code=400, detail="Invalid owner format")
    if not re.match(r'^[a-zA-Z0-9._-]+$', repo) or len(repo) > 100:
        raise HTTPException(status_code=400, detail="Invalid repo format")

    try:
        repo_data = await get_repository(token, owner, repo)
    except Exception:
        repo_data = None

    stats = _get_repo_stats(owner, repo)
    if repo_data:
        stats["language"] = repo_data.get("language", "")
        stats["stars"] = repo_data.get("stars", 0)
        stats["description"] = repo_data.get("description", "")
        stats["updated_at"] = repo_data.get("updated_at", "")

    return stats
