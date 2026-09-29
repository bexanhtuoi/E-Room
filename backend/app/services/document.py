from sqlmodel import Session

from app.repositories.document import DocumentCrud, document_crud, drop_doc_storage
from app.services.helpers import ensure_owner
from app.shared.exceptions import BadRequestError, DocumentNotFoundError

__all__ = [
    "DocumentCrud",
    "count_documents",
    "create_document",
    "delete_document",
    "document_crud",
    "document_scope",
    "drop_doc_storage",
    "get_document_data",
    "list_documents",
    "update_document",
]


def document_scope(user) -> dict:
    if user.role == "admin":
        return {}

    return {"user_id": user.id}


def list_documents(db: Session, user, skip: int = 0, limit: int = 10) -> list:
    return document_crud.get_many(db, skip=skip, limit=limit, **document_scope(user))


def count_documents(db: Session, user) -> int:
    return document_crud.count(db, **document_scope(user))


def get_document_data(db: Session, user, document_id: int):
    document = document_crud.get_one(db, id=document_id)

    if not document:
        raise DocumentNotFoundError()

    ensure_owner(document.user_id, user)

    return document


def create_document(db: Session, user, document_in):
    if ".." in (document_in.file_path or ""):
        raise BadRequestError(detail="Đường dẫn file không hợp lệ.")

    obj_in_data = document_in.model_dump()
    obj_in_data["user_id"] = user.id

    return document_crud.create(db, obj_in=obj_in_data)


def update_document(db: Session, user, document_id: int, document_in):
    document = get_document_data(db, user, document_id)

    return document_crud.update(db, db_obj=document, obj_in=document_in)


def delete_document(db: Session, user, document_id: int):
    document = get_document_data(db, user, document_id)

    return document_crud.delete(db, db_obj=document)
