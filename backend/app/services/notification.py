from sqlmodel import Session

from app.repositories.notification import notification_crud
from app.services.base import ServiceBase
from app.shared.exceptions import NotAuthorizedError, NotificationNotFoundError

__all__ = [
    "NotificationService",
    "notification_service",
]


class NotificationService(ServiceBase):
    def list_notifications(self, db: Session, user, skip: int = 0, limit: int = 10) -> list:
        return notification_crud.get_many(
            db,
            skip=skip,
            limit=limit,
            user_id=user.id,
        )



    def count_notifications(self, db: Session, user) -> int:
        return notification_crud.count(db, user_id=user.id)



    def create_notification(self, db: Session, user, notification_in):
        obj_in_data = notification_in.model_dump()
        obj_in_data["user_id"] = user.id

        return notification_crud.create(db, obj_in=obj_in_data)



    def get_own_notification(self, db: Session, user, notification_id: int):
        notification = self.one_or_404(
            notification_crud.get_one, NotificationNotFoundError, db, id=notification_id,
        )

        if notification.user_id != user.id:
            raise NotAuthorizedError()

        return notification



    def update_notification(self, db: Session, user, notification_id: int, notification_in):
        notification = self.get_own_notification(db, user, notification_id)

        return notification_crud.update(db, db_obj=notification, obj_in=notification_in)



    def delete_notification(self, db: Session, user, notification_id: int):
        notification = self.get_own_notification(db, user, notification_id)

        return notification_crud.delete(db, db_obj=notification)



notification_service = NotificationService()
