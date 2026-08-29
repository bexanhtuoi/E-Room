from sqlmodel import Session, select

from app.models import Notification, NotificationType, User


def seed_notifications(session: Session) -> int:
    users = session.exec(select(User).where(User.email.in_(["nam@gmail.com", "linh@gmail.com"]))).all()
    if len(users) < 2:
        return 0

    notifications = [
        {
            "user_id": users[0].id,
            "title": "Room matched",
            "body": "You matched with a new partner.",
            "notification_type": NotificationType.MATCH,
            "is_read": False,
        },
        {
            "user_id": users[1].id,
            "title": "Session review ready",
            "body": "Your session score is ready to view.",
            "notification_type": NotificationType.REVIEW,
            "is_read": True,
        },
        {
            "user_id": users[0].id,
            "title": "Welcome to ERoom",
            "body": "Complete your profile to get better matches.",
            "notification_type": NotificationType.SYSTEM,
            "is_read": False,
        },
    ]

    inserted = 0
    for data in notifications:
        existing = session.exec(
            select(Notification).where(
                Notification.user_id == data["user_id"],
                Notification.title == data["title"],
            )
        ).first()
        if existing is None:
            session.add(Notification(**data))
            inserted += 1
    if inserted > 0:
        session.commit()
    return inserted