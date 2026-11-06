"""Security & Deep Analysis API.

Endpoints:
- POST  /api/security/{owner}/{repo}/scan?branch=&force=   start deep scan (background)
- GET   /api/security/{owner}/{repo}/scan/{job_id}         poll job status
- GET   /api/security/{owner}/{repo}/report                full report (posture, cards,
                                                           findings, coverage, deps,
                                                           priority queue)
- GET   /api/security/{owner}/{repo}/coverage              coverage section only
- PATCH /api/security/{owner}/{repo}/findings/status       review decision for a finding
"""

from __future__ import annotations

import re

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel

from app.services.deep_scan import create_deep_job, get_deep_job, run_deep_scan
from app.services.findings_store import (
    STATUS_LABELS,
    load_security_report,
    set_finding_status,
)
from app.services.intelligence import repo_id
from app.services.session import SESSION_COOKIE, decode_session

router = APIRouter(prefix="/security", tags=["security"])


def _get_token(request: Request) -> str:
    cookie = request.cookies.get(SESSION_COOKIE)
    if not cookie:
        raise HTTPException(status_code=401, detail="Not authenticated")
    session = decode_session(cookie)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return session["token"]


def _validate(owner: str, repo: str) -> None:
    if not re.match(r"^[a-zA-Z0-9._-]+$", owner) or len(owner) > 100:
        raise HTTPException(status_code=400, detail="Invalid owner format")
    if not re.match(r"^[a-zA-Z0-9._-]+$", repo) or len(repo) > 100:
        raise HTTPException(status_code=400, detail="Invalid repo format")


@router.post("/{owner}/{repo}/scan")
async def start_scan(
    request: Request,
    background_tasks: BackgroundTasks,
    owner: str,
    repo: str,
    branch: str = "main",
    force: bool = True,
):
    token = _get_token(request)
    _validate(owner, repo)
    rid = repo_id(owner, repo)
    existing = load_security_report(rid)
    if existing and not force and existing.get("branch") == branch:
        return {"cached": True, "job_id": None}
    job = create_deep_job(owner, repo, branch)
    background_tasks.add_task(run_deep_scan, job.id, token)
    return {"cached": False, "job_id": job.id}


@router.get("/{owner}/{repo}/scan/{job_id}")
async def scan_status(request: Request, owner: str, repo: str, job_id: str):
    _get_token(request)
    _validate(owner, repo)
    job = get_deep_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Scan job not found")
    return {"job": job.to_dict()}


@router.get("/{owner}/{repo}/report")
async def get_report(request: Request, owner: str, repo: str):
    _get_token(request)
    _validate(owner, repo)
    report = load_security_report(repo_id(owner, repo))
    if not report:
        return {"available": False}
    report["available"] = True
    # never expose stored override internals beyond what the UI needs
    return report


@router.get("/{owner}/{repo}/coverage")
async def get_coverage(request: Request, owner: str, repo: str):
    _get_token(request)
    _validate(owner, repo)
    report = load_security_report(repo_id(owner, repo))
    if not report:
        return {"available": False}
    return {"available": True, "coverage": report.get("coverage"),
            "generated_at": report.get("generated_at")}


class FindingStatusUpdate(BaseModel):
    fingerprint: str
    status: str
    note: str = ""


@router.patch("/{owner}/{repo}/findings/status")
async def update_finding_status(
    request: Request,
    owner: str,
    repo: str,
    body: FindingStatusUpdate,
):
    _get_token(request)
    _validate(owner, repo)
    if len(body.note) > 2000:
        raise HTTPException(status_code=400, detail="Note too long (max 2000 chars)")
    rid = repo_id(owner, repo)
    report = load_security_report(rid)
    if not report:
        raise HTTPException(status_code=404, detail="No security report for this repository")

    try:
        entry = set_finding_status(rid, body.fingerprint, body.status, body.note)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # reflect the change in the persisted findings list immediately
    from app.services.findings_store import apply_statuses
    updated = apply_statuses(report.get("findings", []), report["status_overrides"])
    report["findings"] = updated
    posture = None
    if report.get("posture"):
        from app.services.security_scoring import compute_security_posture
        executed_rules = sorted({
            f.get("rule_id") for f in updated if f.get("category_label") == "security"
        } - {None})
        posture = compute_security_posture(executed_rules, updated,
                                           report["status_overrides"])
        report["posture"] = posture
    from app.services.findings_store import save_security_report
    save_security_report(rid, report)

    return {
        "status": "ok",
        "finding_status": entry,
        "status_label": STATUS_LABELS.get(body.status, body.status),
        "posture": posture,
    }
