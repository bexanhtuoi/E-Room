from datetime import datetime
from typing import Optional

from sqlmodel import Column, Field, Relationship, SQLModel, String, Text

from app.utils.datetime_utils import now_utc


class PronunciationScore(SQLModel, table=True):
    """Điểm phát âm 1 lượt nói — nguồn thật trong DB (đồng nhất cho
    session feedback, thống kê, rescore).

    JSONL speech log (backend/log/speech) giữ vai trò log raw/audio;
    mỗi lần chấm xong (POST .../score) và mỗi lần xin nhận xét
    (POST .../feedback) đều write-through vào bảng này.
    Máy host tự tính (scorer local), bảng này chỉ lưu KẾT QUẢ.
    """

    __tablename__ = "pronunciation_scores"

    id: Optional[int] = Field(default=None, primary_key=True)
    room_id: int = Field(foreign_key="rooms.id", index=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    # Link message DB (None với log cũ chưa có message_id).
    message_id: Optional[int] = Field(default=None, index=True)
    # Session đang mở lúc chấm (best-effort, None nếu không resolve được).
    session_id: Optional[int] = Field(default=None, foreign_key="sessions.id", index=True)
    scored_text: str = Field(default="", sa_column=Column(String(4000)))
    overall: float = Field(default=0.0)
    sounds: float = Field(default=0.0)
    stress: float = Field(default=0.0)
    fluency: float = Field(default=0.0)
    completeness: float = Field(default=0.0)
    method: str = Field(default="", sa_column=Column(String(64)))
    scorer_version: str = Field(default="", sa_column=Column(String(64)))
    # Full ScoringReport (word_details, phonemes, top_errors, warnings).
    report_json: str = Field(default="{}", sa_column=Column(Text))
    # Nhận xét AI (None cho tới khi POST .../feedback).
    feedback_json: Optional[str] = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(default_factory=now_utc, nullable=False)
    updated_at: datetime = Field(default_factory=now_utc, nullable=False)

    room: "Room" = Relationship()
    user: "User" = Relationship()
