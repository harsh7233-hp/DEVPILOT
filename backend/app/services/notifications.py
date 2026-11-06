"""Notification service — event-driven notifications backed by JSON persistence.

All notifications are derived from real repository events. Nothing is fabricated.
Notifications are stored per-session in ``data/notifications/{session_id}.json``.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from typing import Any, Dict, List, Optional

_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
_NOTIF_DIR = os.path.join(_DATA_DIR, "notifications")

CATEGORIES = {"security", "performance", "repository", "pipeline", "dependency", "analysis", "system"}

SEVERITIES = {"critical", "high", "medium", "low", "info"}


def _notif_path(session_id: str) -> str:
    return os.path.join(_NOTIF_DIR, f"{session_id}.json")


def _load(session_id: str) -> List[Dict[str, Any]]:
    try:
        with open(_notif_path(session_id)) as fh:
            return json.load(fh)
    except Exception:
        return []


def _save(session_id: str, notifications: List[Dict[str, Any]]) -> None:
    try:
        os.makedirs(_NOTIF_DIR, exist_ok=True)
        with open(_notif_path(session_id), "w") as fh:
            json.dump(notifications, fh, indent=2)
    except Exception:
        pass


def create_notification(
    session_id: str,
    *,
    category: str,
    title: str,
    message: str,
    severity: str = "info",
    icon: str = "",
    href: str = "",
    entity_type: str = "",
    entity_id: str = "",
    owner: str = "",
    repo: str = "",
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create and persist a notification from a real event."""
    if category not in CATEGORIES:
        category = "system"
    if severity not in SEVERITIES:
        severity = "info"

    notif = {
        "id": str(uuid.uuid4()),
        "category": category,
        "title": title,
        "message": message,
        "severity": severity,
        "icon": icon or _default_icon(category, severity),
        "href": href,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "owner": owner,
        "repo": repo,
        "read": False,
        "created_at": int(time.time()),
        "meta": meta or {},
    }

    notifications = _load(session_id)
    notifications.insert(0, notif)
    # keep max 200 notifications
    if len(notifications) > 200:
        notifications = notifications[:200]
    _save(session_id, notifications)
    return notif


def get_notifications(
    session_id: str,
    *,
    category: Optional[str] = None,
    unread_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> Dict[str, Any]:
    """Return paginated notifications with metadata."""
    notifications = _load(session_id)

    if category:
        notifications = [n for n in notifications if n.get("category") == category]
    if unread_only:
        notifications = [n for n in notifications if not n.get("read")]

    total = len(notifications)
    unread = sum(1 for n in _load(session_id) if not n.get("read"))
    page = notifications[offset: offset + limit]

    return {
        "notifications": page,
        "total": total,
        "unread": unread,
        "offset": offset,
        "limit": limit,
    }


def mark_read(session_id: str, notification_id: str) -> bool:
    """Mark a single notification as read. Returns True if found."""
    notifications = _load(session_id)
    for n in notifications:
        if n["id"] == notification_id:
            n["read"] = True
            _save(session_id, notifications)
            return True
    return False


def mark_all_read(session_id: str) -> int:
    """Mark all notifications as read. Returns count of newly read items."""
    notifications = _load(session_id)
    count = 0
    for n in notifications:
        if not n.get("read"):
            n["read"] = True
            count += 1
    if count > 0:
        _save(session_id, notifications)
    return count


def delete_notification(session_id: str, notification_id: str) -> bool:
    """Delete a single notification. Returns True if found."""
    notifications = _load(session_id)
    before = len(notifications)
    notifications = [n for n in notifications if n["id"] != notification_id]
    if len(notifications) < before:
        _save(session_id, notifications)
        return True
    return False


def get_unread_count(session_id: str) -> int:
    """Return count of unread notifications."""
    return sum(1 for n in _load(session_id) if not n.get("read"))


def _default_icon(category: str, severity: str) -> str:
    icons = {
        "security": "shield",
        "performance": "zap",
        "repository": "git-branch",
        "pipeline": "pipeline",
        "dependency": "package",
        "analysis": "sparkles",
        "system": "alert-circle",
    }
    return icons.get(category, "bell")
