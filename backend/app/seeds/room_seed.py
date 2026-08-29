from sqlmodel import Session, select

from app.models import Room, RoomStatus, User


def seed_rooms(session: Session) -> int:
    host = session.exec(select(User).where(User.email == "huong@gmail.com")).first()
    if host is None:
        return 0

    rooms = [
        {
            "name": "beginner-friendly-chat",
            "topic": "Beginner Friendly Chat",
            "host_id": host.id,
            "max_participants": 5,
            "status": RoomStatus.ACTIVE,
        },
        {
            "name": "business-english-pro",
            "topic": "Business English Pro",
            "host_id": host.id,
            "max_participants": 4,
            "status": RoomStatus.MATCHING,
        },
        {
            "name": "casual-weekend-vibes",
            "topic": "Casual Weekend Vibes",
            "host_id": host.id,
            "max_participants": 8,
            "status": RoomStatus.IDLE,
        },
    ]

    inserted = 0
    for data in rooms:
        existing = session.exec(select(Room).where(Room.name == data["name"])).first()
        if existing is None:
            session.add(Room(**data))
            inserted += 1
    if inserted > 0:
        session.commit()
    return inserted