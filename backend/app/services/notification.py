from app.models import Notification
from app.services.base import CRUDRepository


class NotificationCrud(CRUDRepository):
    def __init__(self) -> None:
        super().__init__(model=Notification)


notification_crud = NotificationCrud()