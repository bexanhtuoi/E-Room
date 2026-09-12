from app.models import Document, DocumentKind
from app.services.base import CRUDRepository


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


class DocumentCrud(CRUDRepository):
    def __init__(self) -> None:
        super().__init__(model=Document)


document_crud = DocumentCrud()
