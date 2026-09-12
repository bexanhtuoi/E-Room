from sqlmodel import Session

from app.integration.redis import delete as redis_delete
from app.models import DocumentKind
from app.services import document_crud, message_crud, notification_crud, room_crud


def drop_doc_storage(doc) -> None:
    if doc.kind != DocumentKind.FILE or not doc.file_path:
        return

    try:
        from app.integration.minio import delete_object

        delete_object(doc.file_path)
    except Exception:
        pass

    try:
        from app.ai.vector_store import delete_document_vectors

        delete_document_vectors(doc.id)
    except Exception:
        pass


def delete_room_cascade(db: Session, room_id: int, with_storage: bool = True) -> None:
    for message in message_crud.get_many(db, room_id=room_id):
        message_crud.delete(db, db_obj=message)

    room_docs = document_crud.get_many(db, room_id=room_id)
    for doc in room_docs:
        document_crud.delete(db, db_obj=doc)

    if with_storage:
        for doc in room_docs:
            drop_doc_storage(doc)

    redis_delete(f"room:{room_id}:participants")
    room = room_crud.get_one(db, id=room_id)
    if room is not None:
        room_crud.delete(db, db_obj=room)


def delete_user_cascade(db: Session, user_id: int) -> None:
    for room in room_crud.get_many(db, host_id=user_id):
        delete_room_cascade(db, room.id)

    for message in message_crud.get_many(db, user_id=user_id):
        message_crud.delete(db, db_obj=message)
    for notif in notification_crud.get_many(db, user_id=user_id):
        notification_crud.delete(db, db_obj=notif)
    for doc in document_crud.get_many(db, user_id=user_id):
        document_crud.delete(db, db_obj=doc)
