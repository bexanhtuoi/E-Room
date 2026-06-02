from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.api.dependencies import get_current_user, get_db_session, get_pagination_params
from app.schemas.series import NotificationListResponse, NotificationResponse
from app.service.notification import NotificationService

router = APIRouter()


def _notification_to_response(n) -> NotificationResponse:
    return NotificationResponse(
        id=str(n.id),
        title=n.title,
        body=n.body,
        notification_type=n.notification_type.value
        if hasattr(n.notification_type, "value")
        else str(n.notification_type),
        action_url=n.action_url,
        is_read=n.is_read,
        created_at=n.created_at.isoformat() if n.created_at else "",
    )


@router.get("/", response_model=NotificationListResponse)
async def list_notifications(
    pagination: tuple[int, int] = Depends(get_pagination_params),
    session: Session = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
) -> NotificationListResponse:
    service = NotificationService(session)
    skip, limit = pagination
    user_id = UUID(current_user["id"])
    items = service.list_for_user(user_id, skip=skip, limit=limit)
    unread = service.count_unread(user_id)
    return NotificationListResponse(
        items=[_notification_to_response(n) for n in items],
        unread_count=unread,
    )


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: UUID,
    session: Session = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
) -> NotificationResponse:
    service = NotificationService(session)
    notification = service.get_by_id(notification_id)
    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )
    if str(notification.user_id) != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not your notification",
        )
    updated = service.mark_read(notification)
    return _notification_to_response(updated)
