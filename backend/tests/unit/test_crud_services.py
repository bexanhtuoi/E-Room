from __future__ import annotations

from sqlmodel import Session

from app.database import engine
from app.models import MessageRole, NotificationType, RoleEnum, RoomStatus
from app.services import message_crud, notification_crud, room_crud, user_crud


class TestCRUDRepositories:
    def test_user_crud_operations(self):
        with Session(engine) as db:
            # Create
            user = user_crud.create(
                db,
                obj_in={
                    "full_name": "CRUD Test User",
                    "email": "crud_test@test.com",
                    "password_hash": "hashedpassword123",
                    "role": RoleEnum.user,
                },
            )
            assert user.id is not None

            # Get One
            fetched = user_crud.get_one(db, id=user.id)
            assert fetched is not None
            assert fetched.email == "crud_test@test.com"

            # Update
            updated = user_crud.update(db, db_obj=fetched, obj_in={"full_name": "Updated Name"})
            assert updated.full_name == "Updated Name"

            # Count
            count = user_crud.count(db, role=RoleEnum.user)
            assert count >= 1

            # Delete
            user_crud.delete(db, db_obj=updated)
            assert user_crud.get_one(db, id=user.id) is None

    def test_room_crud_operations(self):
        with Session(engine) as db:
            room = room_crud.create(
                db,
                obj_in={
                    "name": "CRUD Room",
                    
                    "status": RoomStatus.ACTIVE,
                    "max_participants": 4,
                },
            )
            assert room.id is not None

            rooms = room_crud.get_many(db, status=RoomStatus.ACTIVE)
            assert any(r.id == room.id for r in rooms)

            room_crud.delete(db, db_obj=room)
            assert room_crud.get_one(db, id=room.id) is None

    def test_message_crud_operations(self):
        with Session(engine) as db:
            room = room_crud.create(db, obj_in={"name": "Msg Room CRUD"})
            msg = message_crud.create(
                db,
                obj_in={
                    "room_id": room.id,
                    "role": MessageRole.USER,
                    "text": "Hello CRUD",
                    "meta_data": '{"test": true}',
                },
            )
            assert msg.id is not None
            assert msg.text == "Hello CRUD"

            msgs = message_crud.get_many(db, room_id=room.id)
            assert len(msgs) == 1

            message_crud.delete(db, db_obj=msg)
            room_crud.delete(db, db_obj=room)

    def test_notification_crud_operations(self):
        with Session(engine) as db:
            user = user_crud.create(
                db,
                obj_in={
                    "full_name": "Notif User",
                    "email": "notif_user@test.com",
                    "password_hash": "pwd123",
                    "role": RoleEnum.user,
                },
            )
            notif = notification_crud.create(
                db,
                obj_in={
                    "user_id": user.id,
                    "title": "Welcome Notification",
                    "body": "Welcome to E-Room",
                    "notification_type": NotificationType.SYSTEM,
                    "is_read": False,
                },
            )
            assert notif.id is not None
            assert notif.is_read is False

            notification_crud.update(db, db_obj=notif, obj_in={"is_read": True})
            refetched = notification_crud.get_one(db, id=notif.id)
            assert refetched.is_read is True

            notification_crud.delete(db, db_obj=refetched)
            user_crud.delete(db, db_obj=user)
