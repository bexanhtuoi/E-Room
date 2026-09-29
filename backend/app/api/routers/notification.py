from typing import List

from fastapi import APIRouter, Depends, Request, status
from sqlmodel import Session

from app.api.dependencies import get_pagination_params, require_auth
from app.database import get_session
from app.schemas import NotificationCreateSchema, NotificationResponse, NotificationUpdateSchema
from app.services import notification as notification_service

router = APIRouter()


@router.get("/", response_model=List[NotificationResponse])
def get_notifications(
    request: Request,
    db: Session = Depends(get_session),
    pagination: tuple[int, int] = Depends(get_pagination_params),
    _: str = Depends(require_auth),
) -> List[NotificationResponse]:
    skip, limit = pagination

    return notification_service.list_notifications(db, request.state.current_user, skip=skip, limit=limit)


@router.get("/count")
def count_notifications(
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> dict:
    count = notification_service.count_notifications(db, request.state.current_user)

    return {"count": count}


@router.post("/", response_model=NotificationResponse, status_code=status.HTTP_201_CREATED)
def create_notification(
    notification_in: NotificationCreateSchema,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> NotificationResponse:
    return notification_service.create_notification(db, request.state.current_user, notification_in)


@router.patch("/{notification_id}", response_model=NotificationResponse)
def update_notification(
    notification_id: int,
    notification_in: NotificationUpdateSchema,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> NotificationResponse:
    return notification_service.update_notification(db, request.state.current_user, notification_id, notification_in)


@router.delete("/{notification_id}", response_model=NotificationResponse)
def delete_notification(
    notification_id: int,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> NotificationResponse:
    return notification_service.delete_notification(db, request.state.current_user, notification_id)
