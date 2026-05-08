from __future__ import annotations

from typing import Generic, TypeVar
from uuid import UUID

from sqlmodel import Session, SQLModel, select

EntityT = TypeVar("EntityT", bound=SQLModel)


class BaseService(Generic[EntityT]):
    def __init__(self, session: Session, model_type: type[EntityT]) -> None:
        self.session = session
        self.model_type = model_type

    def get_by_id(self, entity_id: UUID) -> EntityT | None:
        return self.session.get(self.model_type, entity_id)

    def list_all(self) -> list[EntityT]:
        statement = select(self.model_type)
        return list(self.session.exec(statement))

    def save(self, entity: EntityT) -> EntityT:
        self.session.add(entity)
        self.session.commit()
        self.session.refresh(entity)
        return entity

    def delete(self, entity: EntityT) -> None:
        self.session.delete(entity)
        self.session.commit()
