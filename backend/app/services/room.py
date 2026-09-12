from sqlmodel import Session

from app.integration.redis import delete as redis_delete
from app.models import Room
from app.services.base import CRUDRepository
from app.services.document import document_crud, drop_doc_storage
from app.services.message import message_crud
from app.services.session import session_crud


class RoomCrud(CRUDRepository):
    def __init__(self) -> None:
        super().__init__(model=Room)

    def delete_cascade(self, db: Session, room_id: int, with_storage: bool = True) -> None:
        for message in message_crud.get_many(db, room_id=room_id):
            message_crud.delete(db, db_obj=message)

        for db_session in session_crud.get_many(db, room_id=room_id):
            session_crud.delete(db, db_obj=db_session)

        room_docs = document_crud.get_many(db, room_id=room_id)
        for doc in room_docs:
            document_crud.delete(db, db_obj=doc)

        if with_storage:
            for doc in room_docs:
                drop_doc_storage(doc)

        redis_delete(f"room:{room_id}:participants")
        room = self.get_one(db, id=room_id)
        if room is not None:
            self.delete(db, db_obj=room)


room_crud = RoomCrud()
