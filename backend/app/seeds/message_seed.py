from sqlmodel import Session, select

from app.models import Message, MessageRole, Room, User

# Chi 2 room co san hoi thoai mau de trang chu hien thi sinh dong.
# Cac room con lai de trong that — khong seed user ao.
SEEDED_ROOM_NAMES = ["AI Agents & Automation", "Digital Art & Design"]
MEMBER_EMAILS = ["nam@gmail.com", "linh@gmail.com"]


def seed_messages(session: Session) -> int:
    rooms = session.exec(select(Room).where(Room.name.in_(SEEDED_ROOM_NAMES))).all()
    members = session.exec(select(User).where(User.email.in_(MEMBER_EMAILS))).all()
    if len(rooms) == 0 or len(members) < 2:
        return 0

    room_by_name = {room.name: room for room in rooms}
    if "AI Agents & Automation" not in room_by_name or "Digital Art & Design" not in room_by_name:
        return 0

    messages = [
        {
            "room_id": room_by_name["AI Agents & Automation"].id,
            "user_id": members[0].id,
            "role": MessageRole.USER,
            "text": "Has anyone tried building an agent that books meetings by itself?",
            "meta_data": None,
        },
        {
            "room_id": room_by_name["AI Agents & Automation"].id,
            "user_id": members[1].id,
            "role": MessageRole.USER,
            "text": "Yes! Mine handles calendar invites, but it still asks before sending.",
            "meta_data": None,
        },
        {
            "room_id": room_by_name["AI Agents & Automation"].id,
            "user_id": None,
            "role": MessageRole.AI,
            "text": "@ai is in the room — mention @ai anytime for examples, definitions or follow-up questions.",
            "meta_data": '{"type": "heartbeat"}',
        },
        {
            "room_id": room_by_name["Digital Art & Design"].id,
            "user_id": members[1].id,
            "role": MessageRole.USER,
            "text": "I have been sketching with ink lately, it forces me to commit to every line.",
            "meta_data": None,
        },
        {
            "room_id": room_by_name["Digital Art & Design"].id,
            "user_id": members[0].id,
            "role": MessageRole.USER,
            "text": "Same here — what paper do you use for ink work?",
            "meta_data": None,
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
