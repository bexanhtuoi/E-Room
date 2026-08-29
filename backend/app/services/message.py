from app.models import Message
from app.services.base import CRUDRepository


class MessageCrud(CRUDRepository):
    def __init__(self) -> None:
        super().__init__(model=Message)


message_crud = MessageCrud()