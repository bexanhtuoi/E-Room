from sqlmodel import Session, select

from app.models import Document, User


def seed_documents(session: Session) -> int:
    users = session.exec(select(User).where(User.email.in_(["nam@gmail.com", "linh@gmail.com"]))).all()
    if len(users) < 2:
        return 0

    documents = [
        {
            "user_id": users[0].id,
            "file_name": "phrasal-verbs-guide.pdf",
            "file_type": "pdf",
            "file_path": "documents/phrasal-verbs-guide.pdf",
            "metadata_json": '{"chunks": 24, "language": "en"}',
        },
        {
            "user_id": users[1].id,
            "file_name": "travel-english.docx",
            "file_type": "docx",
            "file_path": "documents/travel-english.docx",
            "metadata_json": '{"chunks": 12, "language": "en"}',
        },
    ]

    inserted = 0
    for data in documents:
        existing = session.exec(
            select(Document).where(
                Document.user_id == data["user_id"],
                Document.file_name == data["file_name"],
            )
        ).first()
        if existing is None:
            session.add(Document(**data))
            inserted += 1
    if inserted > 0:
        session.commit()
    return inserted