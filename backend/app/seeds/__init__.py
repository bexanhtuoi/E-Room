from sqlmodel import Session

from app.seeds.document_seed import seed_documents
from app.seeds.message_seed import seed_messages
from app.seeds.notification_seed import seed_notifications
from app.seeds.room_seed import seed_rooms
from app.seeds.user_seed import seed_admin_user, seed_users


def seed_all(session: Session) -> dict[str, int]:
    return {
        "admins": seed_admin_user(session),
        "users": seed_users(session),
        "rooms": seed_rooms(session),
        "messages": seed_messages(session),
        "notifications": seed_notifications(session),
        "documents": seed_documents(session),
    }
