from __future__ import annotations

import hashlib
import re
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.services.graph import get_all_nodes, get_all_relationships, get_node_detail
from app.services.impact import Graph, ImpactResult, analyze_impact
from app.services.session import SESSION_COOKIE, decode_session

router = APIRouter(prefix="/impact", tags=["impact"])


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


class AnalyzeRequest(BaseModel):
    owner: str
    repo: str
    node_id: str
    max_depth: int = 20


@router.post("/analyze")
async def impact_analyze(request: Request, body: AnalyzeRequest):
    _get_token(request)

    if not re.match(r'^[a-zA-Z0-9._-]+$', body.owner) or len(body.owner) > 100:
        raise HTTPException(status_code=400, detail="Invalid owner format")
    if not re.match(r'^[a-zA-Z0-9._-]+$', body.repo) or len(body.repo) > 100:
        raise HTTPException(status_code=400, detail="Invalid repo format")
    if not body.node_id or len(body.node_id) > 500:
        raise HTTPException(status_code=400, detail="Invalid node_id")
    if body.max_depth < 1 or body.max_depth > 50:
        raise HTTPException(status_code=400, detail="max_depth must be between 1 and 50")

    rid = _repo_id(body.owner, body.repo)

    nodes_resp = get_all_nodes(rid)
    rels_resp = get_all_relationships(rid)

    if not nodes_resp:
        raise HTTPException(status_code=404, detail="Graph not found. Build it first.")

    nodes = [dict(r["n"]) for r in nodes_resp]
    relationships = rels_resp

    graph = Graph(nodes, relationships)

    result: ImpactResult = analyze_impact(graph, body.node_id, body.max_depth)
    return result.to_dict()


@router.get("/{owner}/{repo}/impact/{node_id:path}")
async def impact_analyze_get(
    request: Request,
    owner: str,
    repo: str,
    node_id: str,
    max_depth: int = 20,
):
    _get_token(request)
    rid = _repo_id(owner, repo)

    nodes_resp = get_all_nodes(rid)
    rels_resp = get_all_relationships(rid)

    if not nodes_resp:
        raise HTTPException(status_code=404, detail="Graph not found. Build it first.")

    nodes = [dict(r["n"]) for r in nodes_resp]
    relationships = rels_resp

    graph = Graph(nodes, relationships)

    result: ImpactResult = analyze_impact(graph, node_id, max_depth)
    return result.to_dict()
