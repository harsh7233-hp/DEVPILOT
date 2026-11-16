from __future__ import annotations

import hashlib
import re
from typing import Dict, List, Optional

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


def _node_aliases(node: Dict) -> set:
    name = str(node.get("name", "")).strip()
    class_name = str(node.get("class_name", "")).strip()
    file_path = str(node.get("file_path", "") or node.get("path", "")).strip()
    aliases = {name.lower()} if name else set()
    if class_name and name:
        aliases.update({
            f"{class_name}.{name}".lower(),
            f"{class_name}::{name}".lower(),
            f"{class_name}#{name}".lower(),
        })
    if file_path:
        aliases.add(file_path.lower())
    return aliases


def _resolve_node_id(nodes: List[Dict], raw: str) -> str:
    """Accept a real node id or a human-readable name/file path."""
    target = raw.strip()
    if not target:
        return target
    lower = target.lower()

    for n in nodes:
        if str(n.get("node_id", "")) == target:
            return target

    for n in nodes:
        if lower in _node_aliases(n):
            return n.get("node_id", target)

    candidates = []
    for n in nodes:
        if any(lower in alias for alias in _node_aliases(n)):
            candidates.append(n)

    if candidates:
        candidates.sort(
            key=lambda n: (
                len(str(n.get("name", ""))),
                len(str(n.get("file_path", "") or n.get("path", ""))),
            )
        )
        return candidates[0].get("node_id", target)

    return target


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

    nodes = nodes_resp
    relationships = rels_resp

    graph = Graph(nodes, relationships)

    target_id = _resolve_node_id(nodes, body.node_id)
    result: ImpactResult = analyze_impact(graph, target_id, body.max_depth)
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

    nodes = nodes_resp
    relationships = rels_resp

    graph = Graph(nodes, relationships)

    target_id = _resolve_node_id(nodes, node_id)
    result: ImpactResult = analyze_impact(graph, target_id, max_depth)
    return result.to_dict()
