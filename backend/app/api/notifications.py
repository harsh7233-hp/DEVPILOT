"""Notification API endpoints.

Endpoints:
- GET    /api/notifications                list notifications (paginated, filterable)
- GET    /api/notifications/count          unread count
- POST   /api/notifications                create a notification (from real events)
- PATCH  /api/notifications/{id}/read      mark single notification as read
- POST   /api/notifications/read-all       mark all as read
- DELETE /api/notifications/{id}           delete a notification
"""

from __future__ import annotations

import hashlib
import re
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.services.notifications import (
    CATEGORIES,
    create_notification,
    delete_notification,
    get_notifications,
    get_unread_count,
    mark_all_read,
    mark_read,
)
from app.services.session import SESSION_COOKIE, decode_session

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _session_id(request: Request) -> str:
    cookie = request.cookies.get(SESSION_COOKIE)
    if not cookie:
        raise HTTPException(status_code=401, detail="Not authenticated")
    session = decode_session(cookie)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return hashlib.sha256(session["token"].encode()).hexdigest()[:16]


class CreateNotificationRequest(BaseModel):
    category: str
    title: str
    message: str
    severity: str = "info"
    icon: str = ""
    href: str = ""
    entity_type: str = ""
    entity_id: str = ""
    owner: str = ""
    repo: str = ""


@router.get("")
async def list_notifications(
    request: Request,
    category: Optional[str] = None,
    unread_only: bool = False,
    limit: int = 50,
    offset: int = 0,
):
    sid = _session_id(request)
    if category and category not in CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Invalid category. Valid: {sorted(CATEGORIES)}")
    if limit > 100:
        limit = 100
    return get_notifications(sid, category=category, unread_only=unread_only, limit=limit, offset=offset)


@router.get("/count")
async def notification_count(request: Request):
    sid = _session_id(request)
    return {"unread": get_unread_count(sid)}


@router.post("")
async def create_notif(request: Request, body: CreateNotificationRequest):
    sid = _session_id(request)
    if not body.title or len(body.title) > 200:
        raise HTTPException(status_code=400, detail="Title must be 1-200 characters")
    if not body.message or len(body.message) > 1000:
        raise HTTPException(status_code=400, detail="Message must be 1-1000 characters")
    notif = create_notification(
        sid,
        category=body.category,
        title=body.title,
        message=body.message,
        severity=body.severity,
        icon=body.icon,
        href=body.href,
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        owner=body.owner,
        repo=body.repo,
    )
    return notif


@router.patch("/{notification_id}/read")
async def mark_as_read(request: Request, notification_id: str):
    sid = _session_id(request)
    if not mark_read(sid, notification_id):
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"status": "ok", "unread": get_unread_count(sid)}


@router.post("/read-all")
async def mark_all(request: Request):
    sid = _session_id(request)
    count = mark_all_read(sid)
    return {"status": "ok", "marked_read": count, "unread": 0}


@router.delete("/{notification_id}")
async def delete_notif(request: Request, notification_id: str):
    sid = _session_id(request)
    if not delete_notification(sid, notification_id):
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"status": "ok", "unread": get_unread_count(sid)}
