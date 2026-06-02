from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from app.api.dependencies import get_current_user, get_db_session
from app.model import Tag, UserTag
from app.schemas import CustomTagCreateRequest, TagResponse, UserTagBulkAddRequest
from app.service.tag import TagService, UserTagService

router = APIRouter()


@router.get("/popular", response_model=list[TagResponse])
async def get_popular_tags(limit: int = Query(10, ge=1, le=50), session: Session = Depends(get_db_session)) -> list[TagResponse]:
    tag_service = TagService(session)
    tags = tag_service.get_popular_tags(limit)
    return [TagResponse(id=str(tag.id), name=tag.name, slug=tag.slug, category=tag.category, usage_count=tag.usage_count) for tag in tags]


@router.get("/search", response_model=list[TagResponse])
async def search_tags(q: str = Query(..., min_length=1), limit: int = Query(10, ge=1, le=50), session: Session = Depends(get_db_session)) -> list[TagResponse]:
    tag_service = TagService(session)
    tags = tag_service.search_tags(q, limit)
    return [TagResponse(id=str(tag.id), name=tag.name, slug=tag.slug, category=tag.category, usage_count=tag.usage_count) for tag in tags]


@router.post("/custom", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
async def create_custom_tag(payload: CustomTagCreateRequest, session: Session = Depends(get_db_session)) -> TagResponse:
    tag_service = TagService(session)
    slug = payload.name.strip().lower().replace(" ", "-")
    tag = Tag(name=payload.name, slug=slug, category=payload.category, is_custom=True, approved=False)
    saved_tag = tag_service.save(tag)
    return TagResponse(id=str(saved_tag.id), name=saved_tag.name, slug=saved_tag.slug, category=saved_tag.category, usage_count=saved_tag.usage_count)


@router.post("/bulk-add", response_model=dict[str, int])
async def add_user_tags(
    payload: UserTagBulkAddRequest,
    session: Session = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
) -> dict[str, int]:
    user_id = current_user["id"]
    user_tag_service = UserTagService(session)
    existing_tags = user_tag_service.list_user_tags(user_id)
    existing_tag_ids = {str(t.tag_id) for t in existing_tags}

    attached = 0
    for tag_id in payload.tag_ids:
        if tag_id not in existing_tag_ids:
            user_tag = UserTag(user_id=user_id, tag_id=tag_id)
            user_tag_service.attach_tag(user_tag)
            attached += 1

    return {"attachedCount": attached}
