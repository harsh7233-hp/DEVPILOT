from __future__ import annotations

import hashlib
import re
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.services.ai import answer_question, clear_history
from app.services.graph import get_all_nodes, get_all_relationships
from app.services.grounded_ai import ask_devpilot, build_insights
from app.services.intelligence import load_report as load_intel_report
from app.services.session import SESSION_COOKIE, decode_session
from app.services.architecture_risk import compute_architecture_risk

router = APIRouter(prefix="/ai", tags=["ai"])


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


class ChatRequest(BaseModel):
    owner: str
    repo: str
    question: str


@router.post("/chat")
async def ai_chat(request: Request, body: ChatRequest):
    token = _get_token(request)

    if not re.match(r'^[a-zA-Z0-9._-]+$', body.owner) or len(body.owner) > 100:
        raise HTTPException(status_code=400, detail="Invalid owner format")
    if not re.match(r'^[a-zA-Z0-9._-]+$', body.repo) or len(body.repo) > 100:
        raise HTTPException(status_code=400, detail="Invalid repo format")
    if not body.question or len(body.question) > 5000:
        raise HTTPException(status_code=400, detail="Question must be 1-5000 characters")

    rid = _repo_id(body.owner, body.repo)

    nodes_resp = get_all_nodes(rid)
    rels_resp = get_all_relationships(rid)

    if not nodes_resp:
        raise HTTPException(
            status_code=404,
            detail="Graph not found. Analyze and build the graph first.",
        )

    nodes = nodes_resp
    rels = rels_resp

    result = await answer_question(
        question=body.question,
        nodes=nodes,
        rels=rels,
        owner=body.owner,
        repo=body.repo,
        user_token=token,
    )
    return result


@router.delete("/{owner}/{repo}/history")
async def ai_clear_history(request: Request, owner: str, repo: str):
    token = _get_token(request)
    clear_history(owner, repo, token)
    return {"status": "cleared"}


# ── Module 2: grounded Ask-DevPilot + deterministic insights ─────────

def _load_context_reports(owner: str, repo: str):
    """Load every evidence store relevant for grounding (all optional)."""
    rid = _repo_id(owner, repo)
    from app.services.findings_store import load_security_report
    security = load_security_report(rid)
    intel = load_intel_report(rid)
    risk = compute_architecture_risk(rid)
    return security, intel, risk


class AskRequest(BaseModel):
    owner: str
    repo: str
    question: str


@router.post("/ask")
async def ai_ask(request: Request, body: AskRequest):
    _get_token(request)

    if not re.match(r'^[a-zA-Z0-9._-]+$', body.owner) or len(body.owner) > 100:
        raise HTTPException(status_code=400, detail="Invalid owner format")
    if not re.match(r'^[a-zA-Z0-9._-]+$', body.repo) or len(body.repo) > 100:
        raise HTTPException(status_code=400, detail="Invalid repo format")
    if not body.question or len(body.question) > 2000:
        raise HTTPException(status_code=400, detail="Question must be 1-2000 characters")

    rid = _repo_id(body.owner, body.repo)
    nodes_resp = get_all_nodes(rid)
    rels_resp = get_all_relationships(rid)
    nodes = nodes_resp if nodes_resp else []
    rels = rels_resp or []

    security, intel, risk = _load_context_reports(body.owner, body.repo)

    return await ask_devpilot(
        question=body.question,
        nodes=nodes,
        rels=rels,
        security_report=security,
        intel_report=intel if intel and intel.get("available", True) else intel,
        riskmap=risk,
        owner=body.owner,
        repo=body.repo,
    )


@router.get("/{owner}/{repo}/insights")
async def ai_insights(request: Request, owner: str, repo: str):
    _get_token(request)
    _validate_simple(owner, repo)
    security, intel, risk = _load_context_reports(owner, repo)
    insights = build_insights(intel, security, risk)
    return {
        "insights": insights,
        "generated_by": "deterministic-rules",
        "note": (
            "Insights are derived directly from analysis data (no AI generation). "
            "Each insight links to its underlying evidence."
        ),
    }


def _validate_simple(owner: str, repo: str) -> None:
    if not re.match(r'^[a-zA-Z0-9._-]+$', owner) or len(owner) > 100:
        raise HTTPException(status_code=400, detail="Invalid owner format")
    if not re.match(r'^[a-zA-Z0-9._-]+$', repo) or len(repo) > 100:
        raise HTTPException(status_code=400, detail="Invalid repo format")
