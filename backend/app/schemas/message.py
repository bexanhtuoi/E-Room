from pydantic import BaseModel


class MessageCreate(BaseModel):
    content: str
    conversation_id: str
