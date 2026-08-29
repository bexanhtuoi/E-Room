from app.models import User
from app.services.base import CRUDRepository


class UserCrud(CRUDRepository):
    def __init__(self) -> None:
        super().__init__(model=User)


user_crud = UserCrud()