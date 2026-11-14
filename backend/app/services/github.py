import io
import tarfile
from typing import Any, Dict, List, Optional

import re

import httpx

from app.config import settings

GITHUB_API_BASE = "https://api.github.com"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
MAX_TARBALL_BYTES = 50 * 1024 * 1024
MAX_TARBALL_FILE_BYTES = 1_000_000


class GitHubAPIError(Exception):
    """Raised when GitHub rejects a request that must succeed."""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        self.message = message
        super().__init__(f"GitHub API error {status_code}: {message}")


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


async def get_file_tree_checked(
    token: str, owner: str, repo: str, branch: str = "main"
) -> List[Dict[str, Any]]:
    """Like :func:`get_file_tree`, but raises on auth/rate-limit failures."""
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
            detail = ""
            try:
                detail = response.json().get("message", "")
            except Exception:
                detail = response.text[:200]
            raise GitHubAPIError(
                response.status_code, detail or "Unable to list repository files"
            )
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


async def get_repo_tarball(
    token: str, owner: str, repo: str, branch: str = "main"
) -> Dict[str, str]:
    """Download a repository archive and return ``path -> text`` for text files.

    This uses a single GitHub API request instead of one request per file,
    avoiding rate limits and speeding up analysis. Returns an empty mapping
    when the archive is too large or contains no readable text files.
    """
    api_url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/tarball/{branch}"
    auth_headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }

    async with httpx.AsyncClient(follow_redirects=False, timeout=90.0) as client:
        location: Optional[str] = None
        chunks: List[bytes] = []
        total = 0

        async with client.stream("GET", api_url, headers=auth_headers) as response:
            if response.status_code in (301, 302, 303, 307, 308):
                location = response.headers.get("location")
                if not location:
                    raise GitHubAPIError(
                        response.status_code, "Missing repository archive redirect"
                    )
            elif response.status_code == 200:
                async for chunk in response.aiter_bytes():
                    total += len(chunk)
                    if total > MAX_TARBALL_BYTES:
                        return {}
                    chunks.append(chunk)
            else:
                await response.aread()
                detail = ""
                try:
                    detail = response.json().get("message", "")
                except Exception:
                    detail = response.text[:200]
                raise GitHubAPIError(
                    response.status_code,
                    detail or "Unable to download repository archive",
                )

        if location is not None:
            # Follow the signed redirect without the Authorization header.
            async with client.stream(
                "GET", location, headers={"Accept": "application/octet-stream"}
            ) as stream:
                if stream.status_code != 200:
                    await stream.aread()
                    detail = ""
                    try:
                        detail = stream.json().get("message", "")
                    except Exception:
                        detail = stream.text[:200]
                    raise GitHubAPIError(
                        stream.status_code,
                        detail or "Unable to download repository archive",
                    )

                async for chunk in stream.aiter_bytes():
                    total += len(chunk)
                    if total > MAX_TARBALL_BYTES:
                        return {}
                    chunks.append(chunk)

    contents: Dict[str, str] = {}
    try:
        with tarfile.open(fileobj=io.BytesIO(b"".join(chunks)), mode="r:gz") as tar:
            for member in tar.getmembers():
                if not member.isfile() or member.size > MAX_TARBALL_FILE_BYTES:
                    continue
                parts = member.name.split("/", 1)
                if len(parts) != 2:
                    continue
                fileobj = tar.extractfile(member)
                if fileobj is None:
                    continue
                try:
                    contents[parts[1]] = fileobj.read().decode("utf-8")
                except UnicodeDecodeError:
                    continue
    except (tarfile.TarError, OSError) as exc:
        raise GitHubAPIError(502, f"Unable to read repository archive: {exc}") from exc
    return contents


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
