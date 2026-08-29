from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlmodel import Session

from app.api.dependencies import get_pagination_params, require_auth
from app.database import get_session
from app.schemas import NotificationCreateSchema, NotificationResponse, NotificationUpdateSchema
from app.services import notification_crud

router = APIRouter()


@router.get("/", response_model=List[NotificationResponse])
def get_notifications(
    request: Request,
    db: Session = Depends(get_session),
    pagination: tuple[int, int] = Depends(get_pagination_params),
    _: str = Depends(require_auth),
) -> List[NotificationResponse]:
    skip, limit = pagination
    notifications = notification_crud.get_many(
        db,
        skip=skip,
        limit=limit,
        user_id=request.state.current_user.id,
    )
    return notifications


@router.get("/count")
def count_notifications(
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> dict:
    count = notification_crud.count(db, user_id=request.state.current_user.id)
    return {"count": count}


@router.post("/", response_model=NotificationResponse, status_code=status.HTTP_201_CREATED)
def create_notification(
    notification_in: NotificationCreateSchema,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> NotificationResponse:
    obj_in_data = notification_in.model_dump()
    obj_in_data["user_id"] = request.state.current_user.id
    new_notification = notification_crud.create(db, obj_in=obj_in_data)

    return new_notification


@router.patch("/{notification_id}", response_model=NotificationResponse)
def update_notification(
    notification_id: int,
    notification_in: NotificationUpdateSchema,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> NotificationResponse:
    db_notification = notification_crud.get_one(db, id=notification_id)
    if not db_notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

    if db_notification.user_id != request.state.current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    updated_notification = notification_crud.update(db, db_obj=db_notification, obj_in=notification_in)
    return updated_notification


@router.delete("/{notification_id}", response_model=NotificationResponse)
def delete_notification(
    notification_id: int,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> NotificationResponse:
    db_notification = notification_crud.get_one(db, id=notification_id)
    if not db_notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

    if db_notification.user_id != request.state.current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    deleted_notification = notification_crud.delete(db, db_obj=db_notification)
    return deleted_notification

