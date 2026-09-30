from sqlmodel import Session

from app import repositories, services
from app.database import engine
from app.models import NotificationType, RoleEnum


class TestRepositorySurface:
    def test_singletons_shared_between_layers(self):
        assert repositories.room_crud is services.room_crud
        assert repositories.user_crud is services.user_crud
        assert repositories.message_crud is services.message_crud
        assert repositories.session_crud is services.session_crud
        assert repositories.document_crud is services.document_crud
        assert repositories.notification_crud is services.notification_crud
        assert repositories.pronunciation_score_crud is services.pronunciation_score_crud

    def test_service_classes_exposed(self):
        from app.services.auth import AuthService, auth_service
        from app.services.document import DocumentService, document_service
        from app.services.message import MessageService, message_service
        from app.services.notification import NotificationService, notification_service
        from app.services.room import RoomService, room_service
        from app.services.session import SessionService, session_service
        from app.services.speech import SpeechService, speech_service
        from app.services.tts import TTSService, tts_service
        from app.services.user import UserService, user_service

        assert isinstance(room_service, RoomService)
        assert isinstance(session_service, SessionService)
        assert isinstance(message_service, MessageService)
        assert isinstance(speech_service, SpeechService)
        assert isinstance(user_service, UserService)
        assert isinstance(document_service, DocumentService)
        assert isinstance(notification_service, NotificationService)
        assert isinstance(auth_service, AuthService)
        assert isinstance(tts_service, TTSService)

    def test_helpers_hold_shared_functions(self):
        from app.services import helpers

        assert helpers.document_scope is not None
        assert helpers.is_session_chat is not None
        assert helpers.coerce_user_id is not None
        assert helpers.parse_room_id is not None
        assert helpers.avatar_marker is not None
        assert helpers.parse_log_time is not None

    def test_crud_through_new_layer(self):
        from app.repositories import notification_crud, user_crud

        with Session(engine) as db:
            user = user_crud.create(
                db,
                obj_in={
                    "full_name": "Repo Layer User",
                    "email": "repo_layer@test.com",
                    "password_hash": "hashedpassword123",
                    "role": RoleEnum.user,
                },
            )
            notif = notification_crud.create(
                db,
                obj_in={
                    "user_id": user.id,
                    "title": "Repo check",
                    "body": "via app.repositories",
                    "notification_type": NotificationType.SYSTEM,
                    "is_read": False,
                },
            )
            assert notification_crud.get_one(db, id=notif.id) is not None

            notification_crud.delete(db, db_obj=notif)
            user_crud.delete(db, db_obj=user)
            assert user_crud.get_one(db, id=user.id) is None
