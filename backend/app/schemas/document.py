from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class DocumentCreateSchema(BaseModel):
    file_name: str
    file_type: str
    file_path: str
    metadata_json: Optional[str] = None


class DocumentUpdateSchema(BaseModel):
    file_name: Optional[str] = None
    metadata_json: Optional[str] = None


class DocumentResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    user_id: int
    file_name: str
    file_type: str
    file_path: str
    metadata_json: Optional[str] = None
    created_at: Optional[datetime] = None