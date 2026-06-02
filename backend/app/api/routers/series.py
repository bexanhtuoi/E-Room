from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.api.dependencies import get_current_user, get_db_session, get_pagination_params
from app.model import (
    RoomSeries,
    SeriesStatus,
    TopicRoom,
    TopicRoomRegistration,
    TopicRoomStatus,
)
from app.schemas.series import (
    SeriesCreateRequest,
    SeriesResponse,
    SeriesUpdateRequest,
    TopicRoomCreateRequest,
    TopicRoomRegistrationRequest,
    TopicRoomResponse,
)
from app.service.series import (
    RoomSeriesService,
    TopicRoomRegistrationService,
    TopicRoomService,
)

router = APIRouter()


def _series_to_response(series: RoomSeries) -> SeriesResponse:
    return SeriesResponse(
        id=str(series.id),
        title=series.title,
        description=series.description,
        creator_id=str(series.creator_id),
        tag_id=str(series.tag_id) if series.tag_id else "",
        total_sessions=series.total_sessions,
        schedule_cron=series.schedule_cron,
        status=series.status.value if hasattr(series.status, "value") else str(series.status),
        created_at=series.created_at.isoformat() if series.created_at else "",
        updated_at=series.updated_at.isoformat() if series.updated_at else "",
    )


def _topic_room_to_response(room: TopicRoom) -> TopicRoomResponse:
    return TopicRoomResponse(
        id=str(room.id),
        title=room.title,
        description=room.description,
        tag_id=str(room.tag_id),
        series_id=str(room.series_id) if room.series_id else None,
        host_user_id=str(room.host_user_id) if room.host_user_id else "",
        is_ai_hosted=room.is_ai_hosted,
        max_participants=room.max_participants,
        registered_count=room.registered_count,
        status=room.status.value if hasattr(room.status, "value") else str(room.status),
        created_at=room.created_at.isoformat() if room.created_at else "",
        updated_at=room.updated_at.isoformat() if room.updated_at else "",
    )


def _get_series_or_404(service: RoomSeriesService, series_id: UUID) -> RoomSeries:
    series = service.get_by_id(series_id)
    if series is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Series not found")
    return series


def _check_series_owner(series: RoomSeries, user_id: str) -> None:
    if str(series.creator_id) != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the creator can modify this series",
        )


def _get_topic_room_or_404(service: TopicRoomService, room_id: UUID) -> TopicRoom:
    room = service.get_by_id(room_id)
    if room is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic room not found")
    return room


def _check_topic_room_not_full(room: TopicRoom) -> None:
    if room.registered_count >= room.max_participants:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Room is full")


def _check_not_already_registered(
    reg_service: TopicRoomRegistrationService,
    room_id: UUID,
    user_id: str,
) -> None:
    existing = reg_service.list_registrations(str(room_id))
    if any(str(r.user_id) == user_id for r in existing):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already registered")


# ─── Series ──────────────────────────────────────────

@router.get("", response_model=list[SeriesResponse])
async def list_series(
    tag_id: str | None = None,
    pagination: tuple[int, int] = Depends(get_pagination_params),
    session: Session = Depends(get_db_session),
) -> list[SeriesResponse]:
    service = RoomSeriesService(session)
    skip, limit = pagination
    if tag_id:
        items = service.list_series_by_tag(tag_id)
    else:
        items = service.list_all()
    return [_series_to_response(s) for s in items[skip : skip + limit]]


@router.post("", response_model=SeriesResponse, status_code=status.HTTP_201_CREATED)
async def create_series(
    payload: SeriesCreateRequest,
    session: Session = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
) -> SeriesResponse:
    service = RoomSeriesService(session)
    series = RoomSeries(
        title=payload.title,
        description=payload.description,
        creator_id=UUID(current_user["id"]),
        tag_id=UUID(payload.tag_id),
        total_sessions=payload.total_sessions,
        schedule_cron=payload.schedule_cron,
        status=SeriesStatus.ACTIVE,
    )
    saved = service.create(session, series.model_dump())
    return _series_to_response(saved)


@router.get("/{series_id}", response_model=SeriesResponse)
async def get_series(
    series_id: UUID,
    session: Session = Depends(get_db_session),
) -> SeriesResponse:
    service = RoomSeriesService(session)
    return _series_to_response(_get_series_or_404(service, series_id))


@router.patch("/{series_id}", response_model=SeriesResponse)
async def update_series(
    series_id: UUID,
    payload: SeriesUpdateRequest,
    session: Session = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
) -> SeriesResponse:
    service = RoomSeriesService(session)
    series = _get_series_or_404(service, series_id)
    _check_series_owner(series, current_user["id"])
    update_data = payload.model_dump(exclude_unset=True)
    updated = service.update(session, series, update_data)
    return _series_to_response(updated)


@router.delete("/{series_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_series(
    series_id: UUID,
    session: Session = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
) -> None:
    service = RoomSeriesService(session)
    series = _get_series_or_404(service, series_id)
    _check_series_owner(series, current_user["id"])
    service.delete(session, series)


# ─── Topic Rooms ────────────────────────────────────

@router.get("/topic-rooms", response_model=list[TopicRoomResponse])
async def list_topic_rooms(
    tag_id: str | None = None,
    series_id: str | None = None,
    pagination: tuple[int, int] = Depends(get_pagination_params),
    session: Session = Depends(get_db_session),
) -> list[TopicRoomResponse]:
    service = TopicRoomService(session)
    skip, limit = pagination
    items = service.list_upcoming_rooms(tag_id)
    if series_id:
        items = [r for r in items if str(r.series_id) == series_id]
    return [_topic_room_to_response(r) for r in items[skip : skip + limit]]


@router.post("/topic-rooms", response_model=TopicRoomResponse, status_code=status.HTTP_201_CREATED)
async def create_topic_room(
    payload: TopicRoomCreateRequest,
    session: Session = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
) -> TopicRoomResponse:
    service = TopicRoomService(session)
    room = TopicRoom(
        title=payload.title,
        description=payload.description,
        tag_id=UUID(payload.tag_id),
        series_id=UUID(payload.series_id) if payload.series_id else None,
        host_user_id=UUID(current_user["id"]),
        is_ai_hosted=payload.is_ai_hosted,
        max_participants=payload.max_participants,
        status=TopicRoomStatus.UPCOMING,
    )
    saved = service.create(session, room.model_dump())
    return _topic_room_to_response(saved)


@router.post("/topic-rooms/{room_id}/register", response_model=dict)
async def register_topic_room(
    room_id: UUID,
    payload: TopicRoomRegistrationRequest,
    session: Session = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
) -> dict:
    topic_service = TopicRoomService(session)
    reg_service = TopicRoomRegistrationService(session)

    room = _get_topic_room_or_404(topic_service, room_id)
    _check_topic_room_not_full(room)
    _check_not_already_registered(reg_service, room_id, current_user["id"])

    registration = TopicRoomRegistration(
        topic_room_id=room_id,
        user_id=UUID(current_user["id"]),
    )
    reg_service.create(session, registration.model_dump())

    room.registered_count += 1
    topic_service.update(session, room, {"registered_count": room.registered_count})

    return {"status": "registered", "room_id": str(room_id)}
