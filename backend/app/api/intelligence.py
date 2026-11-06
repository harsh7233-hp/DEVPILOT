"""Code Intelligence API.

Endpoints:
- POST /api/intelligence/{owner}/{repo}/scan        start scan (background job)
- GET  /api/intelligence/{owner}/{repo}/scan/{id}   poll scan status
- GET  /api/intelligence/{owner}/{repo}/report      cached report (stats/health/issues/recommendations)
- GET  /api/intelligence/{owner}/{repo}/pipelines   CI/CD detection
- GET  /api/intelligence/{owner}/{repo}/risk-map    architecture risk map
- POST /api/intelligence/suggested-change           Groq-generated suggested diff for a finding
"""

from __future__ import annotations

import re

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel

from app.services.ai import _call_llm, _get_api_config
from app.services.architecture_risk import compute_architecture_risk
from app.services.intelligence import (
    create_intel_job,
    get_intel_job,
    load_report,
    repo_id,
    run_intelligence_scan,
)
from app.services.pipelines import detect_pipelines
from app.services.session import SESSION_COOKIE, decode_session

router = APIRouter(prefix="/intelligence", tags=["intelligence"])


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
    force: bool = False,
):
    token = _get_token(request)
    _validate(owner, repo)

    rid = repo_id(owner, repo)
    cached = load_report(rid)
    if cached and not force and cached.get("branch") == branch:
        return {"cached": True, "job_id": None}

    job = create_intel_job(owner, repo, branch)
    background_tasks.add_task(run_intelligence_scan, job.id, token, detect_pipelines)
    return {"cached": False, "job_id": job.id}


@router.get("/{owner}/{repo}/scan/{job_id}")
async def scan_status(request: Request, owner: str, repo: str, job_id: str):
    _get_token(request)
    _validate(owner, repo)
    job = get_intel_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Scan job not found")
    return {"job": job.to_dict()}


@router.get("/{owner}/{repo}/report")
async def get_report(request: Request, owner: str, repo: str):
    _get_token(request)
    _validate(owner, repo)
    report = load_report(repo_id(owner, repo))
    if not report:
        return {"available": False}
    report["available"] = True
    return report


@router.get("/{owner}/{repo}/pipelines")
async def get_pipelines(request: Request, owner: str, repo: str):
    token = _get_token(request)
    _validate(owner, repo)
    report = load_report(repo_id(owner, repo))
    if report and "pipelines" in report:
        return {"available": True, **report["pipelines"]}
    # on-demand fallback (requires an existing analysis tree fetch)
    from app.services.github import get_file_tree

    try:
        pipelines = await detect_pipelines(token, owner, repo, await get_file_tree(token, owner, repo))
        return {"available": pipelines["total"] > 0, **pipelines}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Pipeline detection failed: {exc}")


@router.get("/{owner}/{repo}/risk-map")
async def get_risk_map(request: Request, owner: str, repo: str):
    _get_token(request)
    _validate(owner, repo)
    result = compute_architecture_risk(repo_id(owner, repo))
    result["available"] = bool(result.get("has_graph"))
    return result


class SuggestedChangeRequest(BaseModel):
    file: str
    symbol: str = ""
    problem: str
    evidence: str = ""
    explanation: str = ""
    recommendation: str = ""
    language: str = "TypeScript"


@router.post("/suggested-change")
async def suggested_change(body: SuggestedChangeRequest, request: Request):
    _get_token(request)
    config = _get_api_config()
    if not config:
        raise HTTPException(status_code=503, detail="AI not configured. Set GROQ_API_KEY.")

    prompt = f"""You are a senior software engineer. Based ONLY on the static-analysis finding below,
produce a minimal suggested code change as a unified diff.

Rules:
- Output ONLY the diff inside a single ```diff code block.
- Use correct unified-diff format with --- / +++ headers using the given file path.
- Keep the change small and focused on the finding.
- If context is insufficient to produce a safe diff, output the closest reasonable sketch and add a
  comment line starting with '# note:' explaining assumptions.

File: {body.file}
Language: {body.language}
Symbol: {body.symbol or "(top-level)"}
Problem: {body.problem}
Explanation: {body.explanation}
Recommended direction: {body.recommendation}
Evidence (current code snippet):
{body.evidence[:1200]}
"""

    try:
        diff = await _call_llm(
            [{"role": "user", "content": prompt}],
            temperature=0.2,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI request failed: {exc}")

    m = re.search(r"```(?:diff)?\s*\n(.*?)```", diff, re.DOTALL)
    content = m.group(1).strip() if m else diff.strip()

    return {
        "file": body.file,
        "symbol": body.symbol,
        "diff": content,
        "source": "ai-recommendation",
        "disclaimer": "AI-generated suggestion based on static analysis findings. Review carefully — nothing is applied automatically.",
        "model": config["model"],
    }
