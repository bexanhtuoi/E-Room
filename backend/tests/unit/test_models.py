from __future__ import annotations

from app.models import (
    Document,
    EnglishLevel,
    Message,
    MessageRole,
    Notification,
    NotificationType,
    RoleEnum,
    Room,
    RoomStatus,
    User,
)


class TestDomainModels:
    def test_user_model_defaults_and_fields(self):
        user = User(
            email="test_model@test.com",
            full_name="Model User",
            english_level=EnglishLevel.B2,
        )
        assert user.role == RoleEnum.user
        assert user.created_at is not None
        assert user.updated_at is not None
        assert user.avatar_url is None

    def test_room_model_defaults(self):
        room = Room(name="Test Model Room", host_id=1)
        assert room.status == RoomStatus.IDLE
        assert room.max_participants == 4

    def test_message_model_defaults(self):
        msg = Message(room_id=1, user_id=2, text="Sample text", role=MessageRole.USER)
        assert msg.role == MessageRole.USER
        assert msg.created_at is not None

    def test_notification_model_defaults(self):
        notif = Notification(user_id=1, title="Hello")
        assert notif.notification_type == NotificationType.SYSTEM
        assert notif.is_read is False

    def test_document_model_defaults(self):
        doc = Document(user_id=1, file_name="sample.pdf", file_type="pdf", file_path="docs/sample.pdf")
        assert doc.file_type == "pdf"
        assert doc.created_at is not None
