import hashlib
import hmac
import json
import time
from typing import Any, Dict, Optional
from urllib.parse import quote, unquote

from app.config import settings

SESSION_COOKIE = "devpilot_session"
SESSION_MAX_AGE = 7 * 24 * 60 * 60  # 7 days


def _sign(data: str) -> str:
    return hmac.new(
        settings.session_secret.encode(),
        data.encode(),
        hashlib.sha256,
    ).hexdigest()


def create_session(token: str, user: Dict[str, Any]) -> str:
    payload = json.dumps(
        {"token": token, "user": user, "exp": int(time.time()) + SESSION_MAX_AGE}
    )
    encoded = quote(payload)
    signature = _sign(encoded)
    return f"{encoded}.{signature}"


def decode_session(cookie_value: str) -> Optional[Dict[str, Any]]:
    try:
        parts = cookie_value.rsplit(".", 1)
        if len(parts) != 2:
            return None

        encoded, signature = parts
        expected = _sign(encoded)
        if not hmac.compare_digest(signature, expected):
            return None

        payload = json.loads(unquote(encoded))
        if payload.get("exp", 0) < time.time():
            return None

        return payload
    except Exception:
        return None
