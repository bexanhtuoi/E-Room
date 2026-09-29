from datetime import timedelta

from sqlmodel import Session

from app.config import settings
from app.repositories.user import user_crud
from app.security import create_access_token, hash_password, verify_password
from app.services.base import ServiceBase
from app.shared.exceptions import EmailExistsError, InvalidCredentialsError

__all__ = [
    "AuthService",
    "auth_service",
]


class AuthService(ServiceBase):
    def register_user(self, db: Session, user_in):
        if user_crud.get_one(db, email=user_in.email):
            raise EmailExistsError()

        obj_in_data = user_in.model_dump()
        obj_in_data["password_hash"] = hash_password(obj_in_data.pop("password"))

        return user_crud.create(db, obj_in=obj_in_data)



    def login_user(self, db: Session, username: str, password: str) -> tuple:
        user = user_crud.get_one(db, email=username)

        if not user or not verify_password(password, user.password_hash):
            raise InvalidCredentialsError()

        expires = timedelta(minutes=settings.access_token_expires_minutes)
        token = create_access_token(data=user.id, expires_delta=expires)

        return user, token, expires



auth_service = AuthService()
