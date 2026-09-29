from app.shared.exceptions import NotAuthenticatedError, NotAuthorizedError

__all__ = ["ensure_owner"]


def ensure_owner(owner_id: int, user) -> None:
    if user is None:
        raise NotAuthenticatedError()

    if str(owner_id) == str(user.id):
        return

    if user.role == "admin":
        return

    raise NotAuthorizedError()
