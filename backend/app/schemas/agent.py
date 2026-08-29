from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class AgentEnum(str, Enum):
    auto = "auto"
    knowledge = "knowledge"


class RagMetadata(BaseModel):
    source: Optional[str] = None
    location: Optional[str] = None
    tag: Optional[str] = None


class ShortTermMemoryMessage(BaseModel):
    summary_message: Optional[str] = None
    metadata: Optional[List[RagMetadata]] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, data):
        if isinstance(data, dict):
            if "summary_message" not in data and "summary" in data:
                data["summary_message"] = data.pop("summary")
        return data


class KnowledgeAgentOutput(BaseModel):
    text: str
    image_url: Optional[List[str]] = None


class LongTermMemoryMessage(BaseModel):
    store: bool = False
    memory: Optional[str] = None

    @field_validator("memory", mode="before")
    @classmethod
    def normalize_null_strings(cls, v):
        if isinstance(v, str):
            if v.strip().lower() in {"none", "null", "None", "NULL", "", "n/a", "na", " "}:
                return None
        return v


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str = Field(max_length=32768)


class GradeDocuments(BaseModel):
    binary_score: bool = Field(description="true if relevant, false if not relevant")


class ChatCompletionRequest(BaseModel):
    messages: List[ChatMessage]
    model: Optional[str] = None
    stream: bool = False
    conversation_id: int
    tool_choices: list[str] = []