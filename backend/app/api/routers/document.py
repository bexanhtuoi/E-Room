from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlmodel import Session

from app.api.dependencies import authorize_owner, get_pagination_params, require_auth
from app.database import get_session
from app.schemas import DocumentCreateSchema, DocumentResponse, DocumentUpdateSchema
from app.services import document_crud

router = APIRouter()


@router.get("/", response_model=List[DocumentResponse])
def get_documents(
    db: Session = Depends(get_session),
    pagination: tuple[int, int] = Depends(get_pagination_params),
) -> List[DocumentResponse]:
    skip, limit = pagination
    documents = document_crud.get_many(db, skip=skip, limit=limit)
    return documents


@router.get("/count")
def count_documents(db: Session = Depends(get_session)) -> dict:
    return {"count": document_crud.count(db)}


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(document_id: int, db: Session = Depends(get_session)) -> DocumentResponse:
    db_document = document_crud.get_one(db, id=document_id)
    if not db_document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return db_document


@router.post("/", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def create_document(
    document_in: DocumentCreateSchema,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> DocumentResponse:
    obj_in_data = document_in.model_dump()
    obj_in_data["user_id"] = request.state.current_user.id
    new_document = document_crud.create(db, obj_in=obj_in_data)

    return new_document


@router.patch("/{document_id}", response_model=DocumentResponse)
def update_document(
    document_id: int,
    document_in: DocumentUpdateSchema,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> DocumentResponse:
    db_document = document_crud.get_one(db, id=document_id)
    if not db_document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    authorize_owner(db_document.user_id, request)

    updated_document = document_crud.update(db, db_obj=db_document, obj_in=document_in)
    return updated_document


@router.delete("/{document_id}", response_model=DocumentResponse)
def delete_document(
    document_id: int,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> DocumentResponse:
    db_document = document_crud.get_one(db, id=document_id)
    if not db_document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    authorize_owner(db_document.user_id, request)

    deleted_document = document_crud.delete(db, db_obj=db_document)
    return deleted_document

