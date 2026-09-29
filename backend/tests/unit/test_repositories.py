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

    def test_legacy_names_still_exposed(self):
        from app.services import document as document_service
        from app.services import message as message_service
        from app.services import session as session_service
        from app.services import user as user_service

        assert document_service.drop_doc_storage is not None
        assert message_service.is_recent_duplicate is not None
        assert session_service.is_session_chat is not None
        assert session_service.session_lines is not None
        assert user_service.count_streak is not None
        assert user_service.peak_day is not None

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
