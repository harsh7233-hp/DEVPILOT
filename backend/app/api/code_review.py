from __future__ import annotations

import hashlib
import re
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.services.code_review import review_code, run_static_checks
from app.services.graph import get_all_nodes, get_all_relationships
from app.services.session import SESSION_COOKIE, decode_session

router = APIRouter(prefix="/code-review", tags=["code-review"])


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


class ReviewRequest(BaseModel):
    owner: str
    repo: str
    file_path: str
    code: str
    language: str = "TypeScript"
    entity_name: str = ""
    diff: str = ""


class StaticOnlyRequest(BaseModel):
    code: str
    language: str = "TypeScript"
    file_path: str = ""


@router.post("/review")
async def code_review(request: Request, body: ReviewRequest):
    _get_token(request)

    if not body.code or len(body.code) > 50000:
        raise HTTPException(status_code=400, detail="Code must be 1-50000 characters")
    if body.diff and len(body.diff) > 20000:
        raise HTTPException(status_code=400, detail="Diff must be under 20000 characters")
    if not re.match(r'^[a-zA-Z0-9._-]+$', body.owner) or len(body.owner) > 100:
        raise HTTPException(status_code=400, detail="Invalid owner format")
    if not re.match(r'^[a-zA-Z0-9._-]+$', body.repo) or len(body.repo) > 100:
        raise HTTPException(status_code=400, detail="Invalid repo format")

    nodes = None
    rels = None
    rid = _repo_id(body.owner, body.repo)
    nodes_resp = get_all_nodes(rid)
    if nodes_resp:
        nodes = [dict(r["n"]) for r in nodes_resp]
        rels = get_all_relationships(rid)

    result = await review_code(
        code=body.code,
        language=body.language,
        file_path=body.file_path,
        entity_name=body.entity_name,
        diff=body.diff,
        nodes=nodes,
        rels=rels,
    )
    return result


@router.post("/static")
async def code_review_static(request: Request, body: StaticOnlyRequest):
    _get_token(request)
    if not body.code or len(body.code) > 50000:
        raise HTTPException(status_code=400, detail="Code must be 1-50000 characters")
    issues = run_static_checks(body.code, body.language, body.file_path)
    return {
        "issues": [i.to_dict() for i in issues],
        "total": len(issues),
        "file": body.file_path,
        "language": body.language,
    }
