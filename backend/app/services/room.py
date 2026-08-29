from app.models import Room
from app.services.base import CRUDRepository


class RoomCrud(CRUDRepository):
    def __init__(self) -> None:
        super().__init__(model=Room)


room_crud = RoomCrud()