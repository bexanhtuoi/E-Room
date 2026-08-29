from sqlmodel import Session, select

from app.models import RoleEnum, User
from app.security import hash_password


def seed_admin_user(session: Session) -> int:
    existing = session.exec(select(User).where(User.email == "admin@gmail.com")).first()
    if existing is not None:
        return 0

    admin = User(
        email="admin@gmail.com",
        password_hash=hash_password("123456789"),
        full_name="Admin",
        role=RoleEnum.admin,
    )
    session.add(admin)
    session.commit()
    return 1


def seed_users(session: Session) -> int:
    users = [
        {
            "email": "huong@gmail.com",
            "password_hash": hash_password("123456789"),
            "full_name": "Hương Trần",
            "avatar_url": None,
            "english_level": "B1",
            "role": RoleEnum.user,
        },
        {
            "email": "nam@gmail.com",
            "password_hash": hash_password("123456789"),
            "full_name": "Nam Nguyễn",
            "avatar_url": None,
            "english_level": "A2",
            "role": RoleEnum.user,
        },
        {
            "email": "linh@gmail.com",
            "password_hash": hash_password("123456789"),
            "full_name": "Linh Phạm",
            "avatar_url": None,
            "english_level": "B2",
            "role": RoleEnum.user,
        },
    ]

    inserted = 0
    for data in users:
        existing = session.exec(select(User).where(User.email == data["email"])).first()
        if existing is None:
            session.add(User(**data))
            inserted += 1
    if inserted > 0:
        session.commit()
    return inserted