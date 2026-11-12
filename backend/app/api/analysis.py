from __future__ import annotations

import re

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from app.analyzer.base import analyze_file, detect_language as detect_analyzable_language
from app.services.analysis import (
    create_job,
    detect_language,
    filter_files,
    get_job,
    save_job,
)
from app.services.github import get_file_content, get_file_tree
from app.services.session import SESSION_COOKIE, decode_session

router = APIRouter(prefix="/analysis", tags=["analysis"])


def _get_token(request: Request) -> str:
    cookie = request.cookies.get(SESSION_COOKIE)
    if not cookie:
        raise HTTPException(status_code=401, detail="Not authenticated")
    session = decode_session(cookie)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return session["token"]


async def _run_analysis(job_id: str, token: str) -> None:
    from app.services.analysis import _jobs

    job = _jobs.get(job_id)
    if not job:
        return

    try:
        job.status = "processing"
        job.message = "Fetching repository file tree..."
        job.progress = 0.1

        tree = await get_file_tree(token, job.owner, job.repo, job.branch)

        if not tree:
            job.status = "completed"
            job.message = "Repository is empty or no files found"
            job.progress = 1.0
            return

        job.total_files = len(tree)
        job.progress = 0.4
        job.message = f"Found {len(tree)} files. Filtering source files..."

        filtered = filter_files(tree)
        job.filtered_files = len(filtered)

        job.progress = 0.7
        job.message = f"Processing {len(filtered)} source files..."

        files = []
        parsed = []
        for i, item in enumerate(filtered):
            lang = detect_language(item["path"])
            file_info = {
                "path": item["path"],
                "size": item.get("size", 0),
                "sha": item.get("sha", ""),
                "language": lang,
            }
            files.append(file_info)

            if detect_analyzable_language(item["path"]) is not None:
                try:
                    content = await get_file_content(
                        token, job.owner, job.repo, item["path"], job.branch
                    )
                    if content:
                        analysis = analyze_file(content, item["path"])
                        if analysis:
                            parsed.append(analysis.to_dict())
                except Exception:
                    pass

            if (i + 1) % 25 == 0:
                job.progress = 0.7 + 0.3 * ((i + 1) / len(filtered))
                job.message = f"Analyzing files... {i + 1}/{len(filtered)}"

        job.files = files
        job.parsed_files = parsed
        job.progress = 1.0
        job.status = "completed"
        job.message = f"Analysis complete. {len(parsed)}/{len(files)} files parsed with tree-sitter."

    except Exception as exc:
        job.status = "failed"
        job.message = "Analysis failed"
        job.error = str(exc)

    save_job(job)


@router.post("")
async def start_analysis(
    request: Request,
    background_tasks: BackgroundTasks,
    owner: str = "",
    repo: str = "",
    branch: str = "main",
):
    if not owner or not repo:
        raise HTTPException(status_code=400, detail="owner and repo are required")

    if not re.match(r'^[a-zA-Z0-9._-]+$', owner) or len(owner) > 100:
        raise HTTPException(status_code=400, detail="Invalid owner format")
    if not re.match(r'^[a-zA-Z0-9._-]+$', repo) or len(repo) > 100:
        raise HTTPException(status_code=400, detail="Invalid repo format")
    if not re.match(r'^[a-zA-Z0-9._/-]+$', branch) or len(branch) > 200:
        raise HTTPException(status_code=400, detail="Invalid branch format")

    token = _get_token(request)
    job = create_job(owner, repo, branch)
    background_tasks.add_task(_run_analysis, job.id, token)

    return {"job_id": job.id, "status": job.status}


@router.get("/{job_id}")
async def get_analysis_status(job_id: str, request: Request):
    _get_token(request)  # ensure authenticated

    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    data = job.to_dict()
    data.pop("parsed_files", None)
    return {"job": data}
