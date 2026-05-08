from pydantic import BaseModel


class AgentSelection(BaseModel):
    name: str
    mode: str = "auto"
