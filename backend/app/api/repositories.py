from typing import Optional

from fastapi import APIRouter, HTTPException, Request

from app.services.github import get_branches, get_repositories, get_repository
from app.services.session import SESSION_COOKIE, decode_session

router = APIRouter(prefix="/repositories", tags=["repositories"])


def _get_token(request: Request) -> str:
    cookie = request.cookies.get(SESSION_COOKIE)
    if not cookie:
        raise HTTPException(status_code=401, detail="Not authenticated")
    session = decode_session(cookie)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return session["token"]


@router.get("")
async def list_repositories(
    request: Request,
    search: Optional[str] = None,
    page: int = 1,
    per_page: int = 30,
):
    token = _get_token(request)
    repos = await get_repositories(token, search=search, page=page, per_page=per_page)
    return {"repositories": repos}


@router.get("/{owner}/{repo}")
async def get_repo(owner: str, repo: str, request: Request):
    token = _get_token(request)
    repo_data = await get_repository(token, owner, repo)
    if not repo_data:
        raise HTTPException(status_code=404, detail="Repository not found")
    return {"repository": repo_data}


@router.get("/{owner}/{repo}/branches")
async def list_branches(owner: str, repo: str, request: Request):
    token = _get_token(request)
    branches = await get_branches(token, owner, repo)
    return {"branches": branches}
