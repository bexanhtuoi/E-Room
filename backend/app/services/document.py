from sqlmodel import Session

from app.repositories.document import document_crud
from app.services.base import ServiceBase
from app.services.helpers import document_scope, ensure_owner
from app.shared.exceptions import BadRequestError, DocumentNotFoundError

__all__ = [
    "DocumentService",
    "document_service",
]


class DocumentService(ServiceBase):
    def list_documents(self, db: Session, user, skip: int = 0, limit: int = 10) -> list:
        return document_crud.get_many(db, skip=skip, limit=limit, **document_scope(user))


    def count_documents(self, db: Session, user) -> int:
        return document_crud.count(db, **document_scope(user))


    def get_document_data(self, db: Session, user, document_id: int):
        document = self.one_or_404(document_crud.get_one, DocumentNotFoundError, db, id=document_id)
        ensure_owner(document.user_id, user)

        return document


    def create_document(self, db: Session, user, document_in):
        if ".." in (document_in.file_path or ""):
            raise BadRequestError(detail="Đường dẫn file không hợp lệ.")

        obj_in_data = document_in.model_dump()
        obj_in_data["user_id"] = user.id

        return document_crud.create(db, obj_in=obj_in_data)


    def update_document(self, db: Session, user, document_id: int, document_in):
        document = self.get_document_data(db, user, document_id)

        return document_crud.update(db, db_obj=document, obj_in=document_in)


    def delete_document(self, db: Session, user, document_id: int):
        document = self.get_document_data(db, user, document_id)

        return document_crud.delete(db, db_obj=document)


document_service = DocumentService()
