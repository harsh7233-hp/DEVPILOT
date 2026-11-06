import logging
import secrets
import time
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import RedirectResponse

from app.config import settings
from app.services.github import exchange_code_for_token, get_user
from app.services.session import SESSION_COOKIE, create_session, decode_session

router = APIRouter(prefix="/auth", tags=["auth"])
log = logging.getLogger(__name__)

_oauth_states: dict = {}
_OAUTH_STATE_TTL = 600  # 10 minutes


def _cleanup_expired_states():
    """Remove OAuth states older than TTL to prevent memory leak."""
    now = time.time()
    expired = [k for k, v in _oauth_states.items() if now - v > _OAUTH_STATE_TTL]
    for k in expired:
        _oauth_states.pop(k, None)


@router.get("/github")
async def github_login():
    _cleanup_expired_states()
    state = secrets.token_urlsafe(32)
    _oauth_states[state] = time.time()
    params = urlencode(
        {
            "client_id": settings.github_client_id,
            "redirect_uri": settings.github_redirect_uri,
            "scope": "read:user repo",
            "state": state,
        }
    )
    return RedirectResponse(f"https://github.com/login/oauth/authorize?{params}")


@router.get("/github/callback")
async def github_callback(code: str = "", state: str = ""):
    if not code:
        log.error("OAuth callback missing authorization code")
        raise HTTPException(status_code=400, detail="Missing authorization code")

    if not state or state not in _oauth_states:
        log.warning("OAuth callback invalid or expired state (state=%s)", state[:8] if state else "")
        raise HTTPException(status_code=400, detail="Invalid or expired state parameter. Please try connecting again.")

    created_at = _oauth_states.pop(state, 0)
    if time.time() - created_at > 600:
        raise HTTPException(status_code=400, detail="OAuth state expired. Please try again.")

    token = await exchange_code_for_token(code)
    if not token:
        log.error("OAuth token exchange failed for code=%s", code[:8])
        raise HTTPException(status_code=400, detail="Failed to exchange code for token. Check GitHub OAuth app configuration.")

    user = await get_user(token)
    if not user:
        log.error("Failed to fetch GitHub user info with token")
        raise HTTPException(status_code=400, detail="Failed to fetch user info from GitHub")

    session = create_session(token, user)
    secure = settings.frontend_url.startswith("https")
    redirect = RedirectResponse(f"{settings.frontend_url}/repositories")
    redirect.set_cookie(
        key=SESSION_COOKIE,
        value=session,
        max_age=7 * 24 * 60 * 60,
        httponly=True,
        samesite="none" if secure else "lax",
        secure=secure,
        path="/",
    )
    return redirect


@router.get("/me")
async def get_current_user(request: Request):
    cookie = request.cookies.get(SESSION_COOKIE)
    if not cookie:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session = decode_session(cookie)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    return {"user": session["user"]}


@router.post("/logout")
async def logout(response: Response):
    secure = settings.frontend_url.startswith("https")
    response.delete_cookie(
        key=SESSION_COOKIE,
        path="/",
        secure=secure,
        samesite="none" if secure else "lax",
    )
    return {"status": "ok"}
