from types import SimpleNamespace

import pytest

from app.services.document import document_scope
from app.services.helpers import ensure_owner
from app.services.room import (
    coerce_user_id,
    ensure_room_access,
    filter_visible_rooms,
    parse_room_id,
)
from app.services.user import avatar_marker
from app.shared.exceptions import AppException, NotAuthenticatedError, NotAuthorizedError


def make_user(user_id=7, role="user", email="hocvien@test.com"):
    return SimpleNamespace(id=user_id, role=role, email=email, full_name="Hoc Vien")


def make_room(room_id=3, host_id=7, is_private=False, allowed="[]"):
    return SimpleNamespace(
        id=room_id, host_id=host_id, is_private=is_private, allowed_emails=allowed,
    )


class TestEnsureOwner:
    def test_owner_passes(self):
        ensure_owner(7, make_user(7))

    def test_admin_passes(self):
        ensure_owner(9, make_user(7, role="admin"))

    def test_stranger_fails(self):
        with pytest.raises(NotAuthorizedError):
            ensure_owner(9, make_user(7))

    def test_anonymous_fails(self):
        with pytest.raises(NotAuthenticatedError):
            ensure_owner(9, None)


class TestEnsureRoomAccess:
    def test_public_room_open(self):
        ensure_room_access(make_room(is_private=False), make_user(99))

    def test_host_passes(self):
        ensure_room_access(make_room(host_id=7, is_private=True), make_user(7))

    def test_stranger_blocked_private(self):
        with pytest.raises(NotAuthorizedError):
            ensure_room_access(make_room(host_id=7, is_private=True), make_user(99))

    def test_allowed_email_passes(self):
        room = make_room(host_id=7, is_private=True, allowed='["hocvien@test.com"]')
        ensure_room_access(room, make_user(99))


class TestFilterVisibleRooms:
    def test_anonymous_sees_only_public(self):
        rooms = [make_room(1, is_private=False), make_room(2, is_private=True)]
        assert [room.id for room in filter_visible_rooms(rooms, None)] == [1]

    def test_member_sees_public_plus_own_private(self):
        rooms = [
            make_room(1, is_private=False),
            make_room(2, host_id=7, is_private=True),
            make_room(3, host_id=9, is_private=True),
        ]
        assert [room.id for room in filter_visible_rooms(rooms, make_user(7))] == [1, 2]


class TestRoomIdHelpers:
    def test_parse_room_id(self):
        assert parse_room_id("42") == 42
        assert parse_room_id("abc") is None
        assert parse_room_id("") is None

    def test_coerce_user_id(self):
        assert coerce_user_id("7") == 7
        assert coerce_user_id("ai_worker") is None


class TestSmallHelpers:
    def test_avatar_marker(self):
        assert avatar_marker(7) == "avatar:7"

    def test_document_scope(self):
        assert document_scope(make_user(7, role="admin")) == {}
        assert document_scope(make_user(7)) == {"user_id": 7}

    def test_app_exception_is_base(self):
        assert issubclass(NotAuthorizedError, AppException)
