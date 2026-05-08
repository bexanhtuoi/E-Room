from pydantic import BaseModel


class ConversationCreate(BaseModel):
    title: str
