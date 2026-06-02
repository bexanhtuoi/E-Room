from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock

import pytest

from app.infrastructure.websocket import WebSocketManager


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture
def manager() -> WebSocketManager:
    mgr = WebSocketManager()
    yield mgr
    mgr._rooms.clear()
    mgr._user_rooms.clear()


def _make_ws() -> AsyncMock:
    ws = AsyncMock()
    ws.send_text = AsyncMock()
    return ws


class TestConnect:
    def test_connect_accepts_and_registers_user(self, manager: WebSocketManager) -> None:
        ws = _make_ws()

        async def _test():
            await manager.connect("room-1", "user-a", ws)

        _run(_test())
        ws.accept.assert_awaited_once()
        assert manager.is_user_in_room("room-1", "user-a") is True

    def test_connect_multiple_users_same_room(self, manager: WebSocketManager) -> None:
        ws1 = _make_ws()
        ws2 = _make_ws()

        async def _test():
            await manager.connect("room-1", "user-a", ws1)
            await manager.connect("room-1", "user-b", ws2)

        _run(_test())
        assert manager.room_participant_count("room-1") == 2

    def test_connect_same_user_different_rooms(self, manager: WebSocketManager) -> None:
        ws1 = _make_ws()
        ws2 = _make_ws()

        async def _test():
            await manager.connect("room-1", "user-a", ws1)
            await manager.connect("room-2", "user-a", ws2)

        _run(_test())
        rooms = manager.get_user_rooms("user-a")
        assert rooms == {"room-1", "room-2"}


class TestDisconnect:
    def test_disconnect_removes_user_from_room(self, manager: WebSocketManager) -> None:
        ws = _make_ws()

        async def _test():
            await manager.connect("room-1", "user-a", ws)
            await manager.disconnect("room-1", "user-a")

        _run(_test())
        assert manager.is_user_in_room("room-1", "user-a") is False

    def test_disconnect_cleans_empty_room(self, manager: WebSocketManager) -> None:
        ws = _make_ws()

        async def _test():
            await manager.connect("room-1", "user-a", ws)
            await manager.disconnect("room-1", "user-a")

        _run(_test())
        assert "room-1" not in manager._rooms

    def test_disconnect_cleans_empty_user_rooms(self, manager: WebSocketManager) -> None:
        ws = _make_ws()

        async def _test():
            await manager.connect("room-1", "user-a", ws)
            await manager.disconnect("room-1", "user-a")

        _run(_test())
        assert "user-a" not in manager._user_rooms

    def test_disconnect_nonexistent_user_is_safe(self, manager: WebSocketManager) -> None:
        ws = _make_ws()

        async def _test():
            await manager.connect("room-1", "user-a", ws)
            await manager.disconnect("room-1", "user-b")

        _run(_test())
        assert manager.room_participant_count("room-1") == 1

    def test_disconnect_broadcasts_leave_event(self, manager: WebSocketManager) -> None:
        ws1 = _make_ws()
        ws2 = _make_ws()

        async def _test():
            await manager.connect("room-1", "user-a", ws1)
            await manager.connect("room-1", "user-b", ws2)
            ws1.send_text.reset_mock()
            await manager.disconnect("room-1", "user-b")

        _run(_test())
        ws1.send_text.assert_awaited_once()
        payload = json.loads(ws1.send_text.await_args[0][0])
        assert payload["event"] == "user_left"
        assert payload["user_id"] == "user-b"


class TestBroadcast:
    def test_broadcast_sends_to_all_in_room(self, manager: WebSocketManager) -> None:
        ws1 = _make_ws()
        ws2 = _make_ws()

        async def _test():
            await manager.connect("room-1", "user-a", ws1)
            await manager.connect("room-1", "user-b", ws2)
            ws1.send_text.reset_mock()
            ws2.send_text.reset_mock()
            await manager.broadcast("room-1", {"type": "message", "text": "hello"})

        _run(_test())
        ws1.send_text.assert_awaited_once()
        ws2.send_text.assert_awaited_once()

    def test_broadcast_empty_room_is_safe(self, manager: WebSocketManager) -> None:
        _run(manager.broadcast("empty-room", {"type": "message"}))


class TestSendToUser:
    def test_send_to_user_delivers_to_target(self, manager: WebSocketManager) -> None:
        ws1 = _make_ws()
        ws2 = _make_ws()

        async def _test():
            await manager.connect("room-1", "user-a", ws1)
            await manager.connect("room-1", "user-b", ws2)
            ws1.send_text.reset_mock()
            await manager.send_to_user("room-1", "user-a", {"type": "dm", "text": "hi"})

        _run(_test())
        ws1.send_text.assert_awaited_once()

    def test_send_to_nonexistent_user_returns_silently(self, manager: WebSocketManager) -> None:
        _run(manager.send_to_user("room-1", "ghost-user", {"type": "ping"}))

    def test_send_to_user_disconnects_on_error(self, manager: WebSocketManager) -> None:
        ws = _make_ws()
        ws.send_text.side_effect = RuntimeError("connection lost")

        async def _test():
            await manager.connect("room-1", "user-a", ws)
            await manager.send_to_user("room-1", "user-a", {"type": "ping"})

        _run(_test())
        assert manager.is_user_in_room("room-1", "user-a") is False


class TestParticipantCount:
    def test_initial_count_is_zero(self, manager: WebSocketManager) -> None:
        assert manager.room_participant_count("room-1") == 0

    def test_count_after_connect(self, manager: WebSocketManager) -> None:
        ws = _make_ws()

        async def _test():
            await manager.connect("room-1", "user-a", ws)

        _run(_test())
        assert manager.room_participant_count("room-1") == 1

    def test_count_after_connect_and_disconnect(self, manager: WebSocketManager) -> None:
        ws = _make_ws()

        async def _test():
            await manager.connect("room-1", "user-a", ws)
            await manager.disconnect("room-1", "user-a")

        _run(_test())
        assert manager.room_participant_count("room-1") == 0

    def test_participants_list_returns_user_ids(self, manager: WebSocketManager) -> None:
        ws1 = _make_ws()
        ws2 = _make_ws()

        async def _test():
            await manager.connect("room-1", "user-a", ws1)
            await manager.connect("room-1", "user-b", ws2)

        _run(_test())
        participants = manager.room_participants("room-1")
        assert set(participants) == {"user-a", "user-b"}


class TestExcludeUser:
    def test_exclude_user_not_receiving_own_join_broadcast(
        self, manager: WebSocketManager
    ) -> None:
        ws1 = _make_ws()
        ws2 = _make_ws()

        async def _test():
            await manager.connect("room-1", "user-a", ws1)
            ws1.send_text.reset_mock()
            await manager.connect("room-1", "user-b", ws2)

        _run(_test())
        join_calls = [
            json.loads(c[0][0])
            for c in ws1.send_text.await_args_list
            if c[0]
        ]
        assert len(join_calls) > 0
        for call_data in join_calls:
            if call_data.get("event") == "user_joined" and call_data.get("user_id") == "user-a":
                pytest.fail("User should not receive their own join event")
