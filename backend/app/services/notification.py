from sqlmodel import Session

from app.repositories.notification import NotificationCrud, notification_crud
from app.shared.exceptions import NotAuthorizedError, NotificationNotFoundError

__all__ = [
    "NotificationCrud",
    "count_notifications",
    "create_notification",
    "delete_notification",
    "list_notifications",
    "notification_crud",
    "update_notification",
]


def list_notifications(db: Session, user, skip: int = 0, limit: int = 10) -> list:
    return notification_crud.get_many(
        db,
        skip=skip,
        limit=limit,
        user_id=user.id,
    )


def count_notifications(db: Session, user) -> int:
    return notification_crud.count(db, user_id=user.id)


def create_notification(db: Session, user, notification_in):
    obj_in_data = notification_in.model_dump()
    obj_in_data["user_id"] = user.id

    return notification_crud.create(db, obj_in=obj_in_data)


def get_own_notification(db: Session, user, notification_id: int):
    notification = notification_crud.get_one(db, id=notification_id)

    if not notification:
        raise NotificationNotFoundError()

    if notification.user_id != user.id:
        raise NotAuthorizedError()

    return notification


def update_notification(db: Session, user, notification_id: int, notification_in):
    notification = get_own_notification(db, user, notification_id)

    return notification_crud.update(db, db_obj=notification, obj_in=notification_in)


def delete_notification(db: Session, user, notification_id: int):
    notification = get_own_notification(db, user, notification_id)

    return notification_crud.delete(db, db_obj=notification)
