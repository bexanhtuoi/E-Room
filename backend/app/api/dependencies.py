from fastapi import HTTPException, Query, Request, status

from app.models.user import User
from app.schemas.room import emails_from_json


def get_pagination_params(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
) -> tuple[int, int]:
    return skip, limit


def require_auth(request: Request) -> str:
    user: User = request.state.current_user

    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authenticated",
        )

    return str(user.id)


def authorize_owner(owner_id: int, request: Request) -> None:
    user: User = request.state.current_user

    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authenticated",
        )

    if str(owner_id) == str(user.id):
        return

    if user.role == "admin":
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Not authorized",
    )


def authorize_room_access(room, request: Request) -> None:
    # Phong public: ai co tai khoan cung vao duoc.
    # Phong private: chi host, admin va email duoc phep.
    if not room.is_private:
        return

    user: User = request.state.current_user
    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authenticated",
        )

    if str(room.host_id) == str(user.id):
        return

    if user.role == "admin":
        return

    allowed = emails_from_json(room.allowed_emails)
    if user.email and user.email.strip().lower() in allowed:
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="This room is private",
    )