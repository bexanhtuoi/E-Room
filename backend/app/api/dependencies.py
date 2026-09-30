from fastapi import Query, Request

from app.models.user import User
from app.schemas.room import emails_from_json
from app.shared.exceptions import NotAuthenticatedError, NotAuthorizedError


def get_pagination_params(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
) -> tuple[int, int]:
    return skip, limit


def require_auth(request: Request) -> str:
    user: User = request.state.current_user

    if not user:
        raise NotAuthenticatedError()

    return str(user.id)


def authorize_owner(owner_id: int, request: Request) -> None:
    user: User = request.state.current_user

    if not user:
        raise NotAuthenticatedError()

    if str(owner_id) == str(user.id):
        return

    if user.role == "admin":
        return

    raise NotAuthorizedError()


def authorize_room_access(room, request: Request) -> None:
    # Phòng public: ai có tài khoản cũng vào được.
    # Phòng private: chỉ host, admin và email được phép.
    if not room.is_private:
        return

    user: User = request.state.current_user
    if not user:
        raise NotAuthenticatedError()

    if str(room.host_id) == str(user.id):
        return

    if user.role == "admin":
        return

    allowed = emails_from_json(room.allowed_emails)
    if user.email and user.email.strip().lower() in allowed:
        return

    raise NotAuthorizedError(detail="Phòng này là riêng tư.")
