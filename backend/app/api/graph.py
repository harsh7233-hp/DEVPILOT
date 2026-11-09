from __future__ import annotations

import hashlib

from fastapi import APIRouter, HTTPException, Request

from app.services.analysis import get_jobs_for_repo
from app.services.graph import (
    build_graph_from_parsed,
    delete_graph,
    get_all_nodes,
    get_all_relationships,
    get_graph_summary,
    get_node_detail,
    suspend_graph_saves,
)
from app.services.session import SESSION_COOKIE, decode_session

router = APIRouter(prefix="/repositories", tags=["graph"])


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


@router.post("/{owner}/{repo}/graph/build")
async def build_graph(
    request: Request,
    owner: str,
    repo: str,
    branch: str = "main",
):
    _get_token(request)
    rid = _repo_id(owner, repo)

    jobs = get_jobs_for_repo(owner, repo)
    completed = [j for j in jobs if j.status == "completed"]
    if not completed:
        raise HTTPException(
            status_code=400,
            detail="No completed analysis found. "
            "Run an analysis first via POST /api/analysis.",
        )

    latest = max(completed, key=lambda j: j.id)
    with suspend_graph_saves():
        result = build_graph_from_parsed(
            rid, owner, repo, latest.parsed_files, latest.files
        )
    return result


@router.get("/{owner}/{repo}/graph")
async def get_graph(
    request: Request,
    owner: str,
    repo: str,
):
    _get_token(request)
    rid = _repo_id(owner, repo)

    summary = get_graph_summary(rid)
    if summary is None:
        raise HTTPException(status_code=404, detail="Graph not found. Build it first.")
    return summary


@router.get("/{owner}/{repo}/graph/node/{node_id:path}")
async def get_node(
    request: Request,
    owner: str,
    repo: str,
    node_id: str,
):
    _get_token(request)
    rid = _repo_id(owner, repo)

    detail = get_node_detail(rid, node_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Node not found")
    return detail


@router.get("/{owner}/{repo}/graph/nodes")
async def list_nodes(
    request: Request,
    owner: str,
    repo: str,
    label: str = "",
):
    _get_token(request)
    rid = _repo_id(owner, repo)
    nodes = get_all_nodes(rid, label or None)
    return {"nodes": [dict(n["n"]) for n in nodes]}


@router.get("/{owner}/{repo}/graph/relationships")
async def list_relationships(
    request: Request,
    owner: str,
    repo: str,
):
    _get_token(request)
    rid = _repo_id(owner, repo)
    rels = get_all_relationships(rid)
    return {"relationships": rels}


@router.delete("/{owner}/{repo}/graph")
async def delete_repo_graph(
    request: Request,
    owner: str,
    repo: str,
):
    _get_token(request)
    rid = _repo_id(owner, repo)
    deleted = delete_graph(rid)
    return {"deleted": deleted, "repo_id": rid}
