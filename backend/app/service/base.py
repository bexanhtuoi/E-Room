from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel

EntityT = TypeVar("EntityT", bound=BaseModel)


class BaseService(Generic[EntityT]):
    def __init__(self) -> None:
        self._items: dict[str, EntityT] = {}

    def get_by_id(self, entity_id: str) -> EntityT | None:
        return self._items.get(entity_id)

    def list_all(self) -> list[EntityT]:
        return list(self._items.values())

    def save(self, entity: EntityT) -> EntityT:
        self._items[str(entity.id)] = entity
        return entity

    def delete(self, entity_id: str) -> None:
        self._items.pop(entity_id, None)
