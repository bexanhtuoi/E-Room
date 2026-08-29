from sqlmodel import Session, select

from app.models import Message, MessageRole, Room, User


def seed_messages(session: Session) -> int:
    room = session.exec(select(Room).where(Room.name == "beginner-friendly-chat")).first()
    members = session.exec(select(User).where(User.email.in_(["nam@gmail.com", "linh@gmail.com"]))).all()
    if room is None or len(members) < 2:
        return 0

    messages = [
        {
            "room_id": room.id,
            "user_id": members[0].id,
            "role": MessageRole.USER,
            "text": "Hi everyone, nice to meet you!",
            "meta_data": None,
        },
        {
            "room_id": room.id,
            "user_id": members[1].id,
            "role": MessageRole.USER,
            "text": "Hello! Let's talk about our weekends.",
            "meta_data": None,
        },
        {
            "room_id": room.id,
            "user_id": None,
            "role": MessageRole.AI,
            "text": "What is your favorite weekend activity?",
            "meta_data": '{"type": "heartbeat"}',
        },
    ]

    inserted = 0
    for data in messages:
        existing = session.exec(
            select(Message).where(
                Message.room_id == data["room_id"],
                Message.text == data["text"],
            )
        ).first()
        if existing is None:
            session.add(Message(**data))
            inserted += 1
    if inserted > 0:
        session.commit()
    return inserted
