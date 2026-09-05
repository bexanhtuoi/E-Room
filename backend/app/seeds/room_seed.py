import json

from sqlmodel import Session, select

from app.models import Room, RoomStatus, User
from app.schemas.room import normalize_topic_list

MAX_ROOM_SEATS = 4


def seed_rooms(session: Session) -> int:
    host = session.exec(select(User).where(User.email == "huong@gmail.com")).first()
    if host is None:
        return 0

    rooms = [
        {
            "name": "AI Agents & Automation",
            "topics": ["AI Agents", "Automation", "LLM", "Productivity"],
            "description": "Daily standup for builders: what agent did you ship, what broke, and what is next.",
            "host_id": host.id,
            "max_participants": MAX_ROOM_SEATS,
            "status": RoomStatus.ACTIVE,
        },
        {
            "name": "Digital Art & Design",
            "topics": ["Digital Art", "Design", "Illustration"],
            "description": "Show your latest piece, talk process and tools, get honest feedback from the table.",
            "host_id": host.id,
            "max_participants": MAX_ROOM_SEATS,
            "status": RoomStatus.ACTIVE,
        },
        {
            "name": "Startups & Indie Hacking",
            "topics": ["Startups", "Indie Hacking", "Marketing"],
            "description": "Founders and hackers trading launch stories, pricing experiments and growth wins.",
            "host_id": host.id,
            "max_participants": MAX_ROOM_SEATS,
            "status": RoomStatus.IDLE,
        },
        {
            "name": "Cinema & Photography",
            "topics": ["Cinema", "Photography", "Storytelling"],
            "description": "Films we watched, shots we took, and the stories behind them.",
            "host_id": host.id,
            "max_participants": MAX_ROOM_SEATS,
            "status": RoomStatus.IDLE,
        },
        {
            "name": "Tech News Weekly",
            "topics": ["Tech News", "Gadgets", "Internet Culture"],
            "description": "The week's biggest tech stories, debated live in 25 minutes.",
            "host_id": host.id,
            "max_participants": MAX_ROOM_SEATS,
            "status": RoomStatus.IDLE,
        },
        {
            "name": "Music & Culture Club",
            "topics": ["Music", "Culture", "Concerts"],
            "description": "What are you listening to? Bring one track and one story behind it.",
            "host_id": host.id,
            "max_participants": MAX_ROOM_SEATS,
            "status": RoomStatus.IDLE,
        },
    ]

    inserted = 0
    for data in rooms:
        existing = session.exec(select(Room).where(Room.name == data["name"])).first()
        topics = json.dumps(normalize_topic_list(data.pop("topics")))
        if existing is None:
            session.add(Room(**data, topics=topics))
            inserted += 1
        elif not existing.topics or existing.topics == "[]":
            existing.topics = topics
            existing.description = existing.description or data.get("description")
            session.add(existing)
    session.commit()
    return inserted
