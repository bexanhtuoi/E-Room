import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.participant import split_words, stream_to_room


class TestSplitWords:
    def test_split_words_keeps_spacing(self):
        assert split_words("hello world") == ["hello ", "world"]

    def test_split_words_empty(self):
        assert split_words("") == []

    def test_split_words_multiple_spaces(self):
        assert split_words("one  two") == ["one  ", "two"]


def make_mock_room():
    mock_room = MagicMock()
    mock_room.local_participant.publish_data = AsyncMock()
    mock_room.connect = AsyncMock()
    mock_room.disconnect = AsyncMock()
    return mock_room


class TestStreamToRoom:
    @pytest.mark.asyncio
    async def test_publishes_word_pieces_and_returns_full_text(self):
        async def fake_events():
            yield {"kind": "token", "text": "hello world"}
            yield {"kind": "token", "text": " hi"}

        mock_room = make_mock_room()

        with (
            patch("app.ai.participant.rtc.Room", return_value=mock_room),
            patch("app.ai.participant.create_token", return_value="tok"),
            patch("app.ai.participant.asyncio.sleep", new=AsyncMock()),
        ):
            full = await stream_to_room(7, fake_events())

        assert full == "hello world hi"

        calls = mock_room.local_participant.publish_data.call_args_list
        payloads = [json.loads(call.args[0]) for call in calls]

        assert payloads[-1]["is_final"] is True
        assert payloads[-1]["stream_id"] == payloads[0]["stream_id"]

        pieces = [p["chunk"] for p in payloads if not p["is_final"]]
        assert "".join(pieces) == "hello world hi"
        assert all(" " not in p.strip() for p in pieces if p.strip())

    @pytest.mark.asyncio
    async def test_thinking_events_are_flagged_and_excluded_from_saved_text(self):
        async def fake_events():
            yield {"kind": "thinking", "text": "Searching the web…"}
            yield {"kind": "token", "text": "done"}

        mock_room = make_mock_room()

        with (
            patch("app.ai.participant.rtc.Room", return_value=mock_room),
            patch("app.ai.participant.create_token", return_value="tok"),
            patch("app.ai.participant.asyncio.sleep", new=AsyncMock()),
        ):
            full = await stream_to_room(7, fake_events())

        assert full == "done"

        calls = mock_room.local_participant.publish_data.call_args_list
        payloads = [json.loads(call.args[0]) for call in calls]

        thinking = [p for p in payloads if p.get("thinking")]
        assert len(thinking) >= 1
        assert "Searching" in "".join(p["chunk"] for p in thinking)

    @pytest.mark.asyncio
    async def test_plain_string_events_still_treated_as_tokens(self):
        async def fake_events():
            yield "hello"

        mock_room = make_mock_room()

        with (
            patch("app.ai.participant.rtc.Room", return_value=mock_room),
            patch("app.ai.participant.create_token", return_value="tok"),
            patch("app.ai.participant.asyncio.sleep", new=AsyncMock()),
        ):
            assert await stream_to_room(7, fake_events()) == "hello"
