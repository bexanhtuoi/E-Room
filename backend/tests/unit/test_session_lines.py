from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from app.models import MessageRole
from app.services.session import session_lines


def make_message(role, user_id, text):
    return SimpleNamespace(
        role=role,
        user_id=user_id,
        text=text,
        created_at=datetime(2026, 9, 14, 14, 20, tzinfo=timezone.utc),
        meta_data="{}",
    )


def make_session(user_id):
    return SimpleNamespace(
        user_id=user_id,
        room_id=3,
        joined_at=datetime(2026, 9, 14, 14, 0, tzinfo=timezone.utc),
        left_at=datetime(2026, 9, 14, 15, 0, tzinfo=timezone.utc),
    )


class TestSessionLinesSpeaker:
    def test_owner_messages_use_you(self):
        messages = [
            make_message(MessageRole.USER, 9, "@ai hello"),
            make_message(MessageRole.AI, None, "Hi there"),
            make_message(MessageRole.USER, 10, "hello too"),
        ]
        users = [SimpleNamespace(id=9, full_name="Pham Huy Hoang"), SimpleNamespace(id=10, full_name="Other Guy")]

        with (
            patch("app.services.session.message_crud.get_many", return_value=messages),
            patch("app.services.session.user_crud.get_by_ids", return_value=users),
        ):
            lines = session_lines(object(), make_session(9))

        assert [line["speaker"] for line in lines] == ["Pham Huy Hoang", "AI", "Other Guy"]

    def test_multiline_markdown_stays_in_single_body(self):
        messages = [
            make_message(MessageRole.AI, None, "Key points:\n- **Item one:** done\nSee https://x.y/z"),
        ]

        with (
            patch("app.services.session.message_crud.get_many", return_value=messages),
            patch("app.services.session.user_crud.get_by_ids", return_value=[]),
        ):
            lines = session_lines(object(), make_session(9))

        assert len(lines) == 1
        assert lines[0]["speaker"] == "AI"
        assert "- **Item one:** done" in lines[0]["text"]
