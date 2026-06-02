from __future__ import annotations

from unittest.mock import MagicMock

from app.infrastructure.event_bus import EventBus
from app.service.room_state import AgentLevel, RoomStateManager, RoomStatus


class TestRoomStateManager:
    def _make_manager(self, mock_crud=None):
        manager = RoomStateManager()
        if mock_crud is not None:
            manager._redis = mock_crud
        return manager

    def test_get_status_unknown_returns_none(self):
        redis = MagicMock()
        redis.hget.return_value = None
        redis.hset.return_value = 1
        manager = self._make_manager(redis)
        assert manager.get_status("missing") is None

    def test_set_status_calls_hset(self):
        redis = MagicMock()
        redis.hset.return_value = 1
        redis.hget.return_value = {"status": "matching"}
        manager = self._make_manager(redis)
        manager.set_status("room-1", RoomStatus.ACTIVE)
        redis.hset.assert_called_once()

    def test_get_agent_level_unknown_returns_basic(self):
        redis = MagicMock()
        redis.hget.return_value = None
        redis.hset.return_value = 1
        manager = self._make_manager(redis)
        assert manager.get_agent_level("missing") == AgentLevel.BASIC


class TestEventBusSubscribeUnsubscribe:
    def test_subscribe_adds_handler(self):
        bus = EventBus()
        bus._subscribers.clear()

        def h(data):
            pass

        bus.subscribe("ch", h)
        assert h in bus._subscribers["ch"]

    def test_subscribe_twice_appends(self):
        bus = EventBus()
        bus._subscribers.clear()

        def h1(data):
            pass

        def h2(data):
            pass

        bus.subscribe("ch", h1)
        bus.subscribe("ch", h2)
        assert len(bus._subscribers["ch"]) == 2

    def test_unsubscribe_removes_handler(self):
        bus = EventBus()
        bus._subscribers.clear()

        def h(data):
            pass

        bus.subscribe("ch", h)
        bus.unsubscribe("ch", h)
        assert h not in bus._subscribers.get("ch", [])

    def test_unsubscribe_nonexistent_channel_safe(self):
        bus = EventBus()

        def h(data):
            pass

        bus.unsubscribe("nonexistent", h)

    def test_unsubscribe_nonexistent_handler_safe(self):
        bus = EventBus()
        bus._subscribers["ch"] = []

        def h(data):
            pass

        bus.unsubscribe("ch", h)

    def test_subscribe_multiple_channels(self):
        bus = EventBus()
        bus._subscribers.clear()

        def h(data):
            pass

        bus.subscribe("a", h)
        bus.subscribe("b", h)
        assert "a" in bus._subscribers
        assert "b" in bus._subscribers


class TestEventBusPublish:
    def test_publish_calls_redis_publish(self, monkeypatch):
        calls = []

        def mock_publish(channel, payload):
            calls.append((channel, payload))
            return 1

        bus = EventBus()
        monkeypatch.setattr(bus._redis, "publish", mock_publish)

        bus.publish("test-ch", {"key": "value"})
        assert len(calls) == 1
        assert calls[0][0] == "test-ch"
        assert calls[0][1]["key"] == "value"

    def test_publish_returns_int(self, monkeypatch):
        bus = EventBus()
        monkeypatch.setattr(bus._redis, "publish", lambda c, p: 3)

        result = bus.publish("ch", {})
        assert result == 3

    def test_publish_empty_payload(self, monkeypatch):
        bus = EventBus()
        monkeypatch.setattr(bus._redis, "publish", lambda c, p: 1)

        result = bus.publish("ch", {})
        assert result == 1
