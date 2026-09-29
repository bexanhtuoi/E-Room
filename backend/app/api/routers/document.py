from typing import List

from fastapi import APIRouter, Depends, Request, status
from sqlmodel import Session

from app.api.dependencies import get_pagination_params, require_auth
from app.database import get_session
from app.schemas import DocumentCreateSchema, DocumentResponse, DocumentUpdateSchema
from app.services import document as document_service

router = APIRouter()


@router.get("/", response_model=List[DocumentResponse])
def get_documents(
    request: Request,
    db: Session = Depends(get_session),
    pagination: tuple[int, int] = Depends(get_pagination_params),
    _: str = Depends(require_auth),
) -> List[DocumentResponse]:
    skip, limit = pagination

    return document_service.list_documents(db, request.state.current_user, skip=skip, limit=limit)


@router.get("/count")
def count_documents(
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> dict:
    return {"count": document_service.count_documents(db, request.state.current_user)}


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: int,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> DocumentResponse:
    return document_service.get_document_data(db, request.state.current_user, document_id)


@router.post("/", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def create_document(
    document_in: DocumentCreateSchema,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> DocumentResponse:
    return document_service.create_document(db, request.state.current_user, document_in)


@router.patch("/{document_id}", response_model=DocumentResponse)
def update_document(
    document_id: int,
    document_in: DocumentUpdateSchema,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> DocumentResponse:
    return document_service.update_document(db, request.state.current_user, document_id, document_in)


@router.delete("/{document_id}", response_model=DocumentResponse)
def delete_document(
    document_id: int,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> DocumentResponse:
    return document_service.delete_document(db, request.state.current_user, document_id)
