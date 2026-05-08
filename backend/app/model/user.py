from pydantic import BaseModel


class User(BaseModel):
    id: str
    email: str
    full_name: str | None = None
