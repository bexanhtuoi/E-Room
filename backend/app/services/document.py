from app.models import Document
from app.services.base import CRUDRepository


class DocumentCrud(CRUDRepository):
    def __init__(self) -> None:
        super().__init__(model=Document)


document_crud = DocumentCrud()