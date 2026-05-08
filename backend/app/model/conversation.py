from pydantic import BaseModel


class Conversation(BaseModel):
    id: str
    title: str
