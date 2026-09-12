from datetime import date, datetime, timedelta
from typing import Optional

from sqlmodel import Session

from app.models import User
from app.services.base import CRUDRepository
from app.services.document import document_crud
from app.services.message import message_crud
from app.services.notification import notification_crud
from app.utils.datetime_utils import as_naive_utc, now_utc


def count_streak(active_days: set, today: date) -> int:
    cursor = today if today in active_days else today - timedelta(days=1)

    streak = 0
    while cursor in active_days:
        streak += 1
        cursor -= timedelta(days=1)

    return streak


def peak_day(day_counts: dict) -> tuple[Optional[str], int]:
    if not day_counts:
        return None, 0

    best_day = max(sorted(day_counts), key=lambda day: day_counts[day])

    return best_day.isoformat(), day_counts[best_day]


class UserCrud(CRUDRepository):
    def __init__(self) -> None:
        super().__init__(model=User)

    def delete_cascade(self, db: Session, user_id: int) -> None:
        from app.services.room import room_crud

        for room in room_crud.get_many(db, host_id=user_id):
            room_crud.delete_cascade(db, room.id)

        for message in message_crud.get_many(db, user_id=user_id):
            message_crud.delete(db, db_obj=message)
        for notif in notification_crud.get_many(db, user_id=user_id):
            notification_crud.delete(db, db_obj=notif)
        for doc in document_crud.get_many(db, user_id=user_id):
            document_crud.delete(db, db_obj=doc)

    def week_counts(self, db: Session, user_id: int) -> dict:
        now = as_naive_utc(now_utc())
        today = now.date()
        monday = today - timedelta(days=today.weekday())
        last_monday = monday - timedelta(weeks=1)

        times = message_crud.get_message_times(
            db,
            user_id=user_id,
            since=datetime.combine(last_monday, datetime.min.time()),
        )
        days = [as_naive_utc(moment).date() for moment in times]

        this_week = sum(1 for day in days if day >= monday)
        last_week = sum(1 for day in days if last_monday <= day < monday)

        recent_counts: dict = {}
        for day in days:
            if day >= today - timedelta(days=6):
                recent_counts[day] = recent_counts.get(day, 0) + 1

        best_day, best_count = peak_day(recent_counts)

        return {
            "messages_total": message_crud.count(db, user_id=user_id),
            "messages_this_week": this_week,
            "messages_last_week": last_week,
            "week_delta": this_week - last_week,
            "streak_days": count_streak(set(days), today),
            "most_active_day": best_day,
            "most_active_day_count": best_count,
        }


user_crud = UserCrud()
