from typing import Any, Dict, List, Optional

import re

import httpx

from app.config import settings

GITHUB_API_BASE = "https://api.github.com"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"


async def exchange_code_for_token(code: str) -> Optional[str]:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            GITHUB_TOKEN_URL,
            data={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
                "redirect_uri": settings.github_redirect_uri,
            },
            headers={"Accept": "application/json"},
        )
        if response.status_code != 200:
            return None
        data = response.json()
        if "error" in data:
            return None
        return data.get("access_token")


async def get_user(token: str) -> Optional[Dict[str, Any]]:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{GITHUB_API_BASE}/user",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            },
        )
        if response.status_code != 200:
            return None
        data = response.json()
        return {
            "id": data.get("id"),
            "login": data.get("login"),
            "name": data.get("name"),
            "avatar_url": data.get("avatar_url"),
        }


async def get_repositories(
    token: str,
    search: Optional[str] = None,
    page: int = 1,
    per_page: int = 30,
) -> List[Dict[str, Any]]:
    async with httpx.AsyncClient() as client:
        if search:
            response = await client.get(
                f"{GITHUB_API_BASE}/search/repositories",
                params={"q": f"{search} in:name user:@me", "sort": "updated", "per_page": per_page},
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                },
            )
            if response.status_code != 200:
                return []
            return [
                _serialize_repo(repo)
                for repo in response.json().get("items", [])
            ]

        response = await client.get(
            f"{GITHUB_API_BASE}/user/repos",
            params={
                "sort": "updated",
                "order": "desc",
                "page": page,
                "per_page": min(per_page, 100),
            },
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            },
        )
        if response.status_code != 200:
            return []
        return [_serialize_repo(repo) for repo in response.json()]


async def get_branches(
    token: str, owner: str, repo: str
) -> List[Dict[str, str]]:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{GITHUB_API_BASE}/repos/{owner}/{repo}/branches",
            params={"per_page": 100},
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            },
        )
        if response.status_code != 200:
            return []
        return [
            {"name": branch["name"], "is_default": branch.get("default", False)}
            for branch in response.json()
        ]


async def get_repository(
    token: str, owner: str, repo: str
) -> Optional[Dict[str, Any]]:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{GITHUB_API_BASE}/repos/{owner}/{repo}",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            },
        )
        if response.status_code != 200:
            return None
        return _serialize_repo(response.json())


def _serialize_repo(data: Dict[str, Any]) -> Dict[str, Any]:
    owner = data.get("owner", {})
    return {
        "id": data.get("id"),
        "name": data.get("name"),
        "full_name": data.get("full_name"),
        "description": data.get("description") or "",
        "language": data.get("language") or "Unknown",
        "default_branch": data.get("default_branch", "main"),
        "stars": data.get("stargazers_count", 0),
        "forks": data.get("forks_count", 0),
        "private": data.get("private", False),
        "url": data.get("html_url", ""),
        "owner": {
            "login": owner.get("login", ""),
            "avatar_url": owner.get("avatar_url", ""),
        },
        "updated_at": data.get("updated_at"),
    }


async def get_file_tree(
    token: str, owner: str, repo: str, branch: str = "main"
) -> List[Dict[str, Any]]:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{GITHUB_API_BASE}/repos/{owner}/{repo}/git/trees/{branch}",
            params={"recursive": "1"},
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            },
        )
        if response.status_code != 200:
            return []
        data = response.json()
        return [
            {
                "path": item["path"],
                "type": item["type"],
                "size": item.get("size", 0),
                "sha": item.get("sha", ""),
            }
            for item in data.get("tree", [])
        ]


async def get_file_content(
    token: str, owner: str, repo: str, path: str, ref: str = "main"
) -> Optional[str]:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contents/{path}",
            params={"ref": ref},
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github.v3.raw",
            },
        )
        if response.status_code != 200:
            return None
        return response.text


def _last_page_count(response: httpx.Response, default: int = 0) -> int:
    """Parse the GitHub pagination Link header to get total page count."""
    link = response.headers.get("Link", "")
    m = re.search(r'[?&]page=(\d+)>;\s*rel="last"', link)
    if m:
        return int(m.group(1))
    return default if response.status_code == 204 else 1 if response.status_code == 200 else 0


async def get_contributors_count(
    token: str, owner: str, repo: str
) -> Optional[int]:
    """Total contributor count via paginated contributors endpoint (1 per page)."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contributors",
                params={"per_page": 1, "anon": "true"},
                headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            )
            if response.status_code == 409:  # empty repository
                return 0
            if response.status_code != 200:
                return None
            return _last_page_count(response)
    except Exception:
        return None


async def get_commits_count(token: str, owner: str, repo: str) -> Optional[int]:
    """Total commit count on default branch via pagination Link header."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{GITHUB_API_BASE}/repos/{owner}/{repo}/commits",
                params={"per_page": 1},
                headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            )
            if response.status_code == 409 or response.status_code == 404:
                return 0
            if response.status_code != 200:
                return None
            return _last_page_count(response)
    except Exception:
        return None
