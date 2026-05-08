from __future__ import annotations

from sqlmodel import Session, select

from app.model import Tag, TagCategory

DEFAULT_TAGS: list[tuple[str, TagCategory]] = [
    ("Openclaw", TagCategory.TECHNOLOGY),
    ("Claude", TagCategory.TECHNOLOGY),
    ("Vibe Coding", TagCategory.TECHNOLOGY),
    ("AI/ML", TagCategory.TECHNOLOGY),
    ("Marketing", TagCategory.BUSINESS),
    ("Physics", TagCategory.SCIENCE),
    ("Math", TagCategory.SCIENCE),
    ("DevOps", TagCategory.TECHNOLOGY),
    ("Blockchain", TagCategory.TECHNOLOGY),
    ("UX Design", TagCategory.CREATIVE),
]


def seed_default_tags(session: Session) -> int:
    inserted = 0
    for name, category in DEFAULT_TAGS:
        existing = session.exec(select(Tag).where(Tag.slug == name.lower().replace(" ", "-"))).first()
        if existing is not None:
            continue
        session.add(Tag(name=name, slug=name.lower().replace(" ", "-"), category=category, usage_count=0))
        inserted += 1
    session.commit()
    return inserted
