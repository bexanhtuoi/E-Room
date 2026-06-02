from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.api.dependencies import get_db_session
from app.schemas.series import LeaderboardEntryResponse, LeaderboardResponse
from app.service.series import LeaderboardService
from app.service.user import UserService

router = APIRouter()


@router.get("", response_model=LeaderboardResponse)
async def get_leaderboard(
    tag_id: str | None = None,
    period: str = "weekly",
    week_start: str | None = None,
    session: Session = Depends(get_db_session),
) -> LeaderboardResponse:
    service = LeaderboardService(session)

    if week_start is None:
        ws = date.today() - timedelta(days=date.today().weekday())
        week_start = ws.isoformat()

    # Support period: weekly, monthly, all
    if period == "all":
        entries = list(service.list_all()) if not tag_id else list(service.list_by_tag(tag_id))
    elif period == "monthly":
        # Last 4 weeks
        ws = (date.today() - timedelta(days=date.today().weekday() + 28)).isoformat()
        entries = list(service.list_all()) if not tag_id else list(service.list_by_tag(tag_id))
        entries = [e for e in entries if str(e.week_start) >= ws]
    else:
        entries = [
            e for e in (service.list_all() if not tag_id else service.list_by_tag(tag_id))
            if str(e.week_start) == week_start
        ]

    entries.sort(key=lambda e: e.rank)

    # Enrich with user display names
    user_ids = [e.user_id for e in entries]
    user_service = UserService(session)
    users = user_service.get_users_batch(user_ids) if user_ids else {}

    return LeaderboardResponse(
        week_start=week_start,
        tag_id=tag_id,
        entries=[
            LeaderboardEntryResponse(
                user_id=str(e.user_id),
                display_name=users.get(str(e.user_id), ""),
                tag_id=str(e.tag_id),
                week_start=str(e.week_start),
                speaking_time_seconds=e.speaking_time_seconds,
                avg_score=e.avg_score,
                sessions_count=e.sessions_count,
                rank=e.rank,
            )
            for e in entries
        ],
    )
