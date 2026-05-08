from pydantic import BaseModel


class Document(BaseModel):
    id: str
    name: str
    source: str | None = None
