from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlmodel import Session, select

from app.model import RefreshToken, User
from app.security import create_access_token, create_refresh_token, hash_password, hash_token, verify_password


class AuthService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def register_user(self, email: str, password: str, display_name: str) -> User:
        user = User(email=email, password_hash=hash_password(password), display_name=display_name)
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def authenticate_user(self, email: str, password: str) -> User | None:
        statement = select(User).where(User.email == email)
        user = self.session.exec(statement).first()
        if user is None:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

    def issue_tokens(self, user: User) -> dict[str, str]:
        access_token = create_access_token(str(user.id))
        refresh_token = create_refresh_token(str(user.id))
        refresh_record = RefreshToken(
            user_id=user.id,
            token_hash=hash_token(refresh_token),
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
        self.session.add(refresh_record)
        self.session.commit()
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
        }
