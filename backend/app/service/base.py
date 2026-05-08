from __future__ import annotations

from typing import Generic, TypeVar, Optional, List, Union
from uuid import UUID

from pydantic import BaseModel
from sqlmodel import Session, SQLModel, select

EntityT = TypeVar("EntityT", bound=SQLModel)


class CRUDRepository(Generic[EntityT]):
    """Reusable CRUD operations — inspired by the FlowAssist pattern.
    
    Usable standalone (dependency-injected) or as the engine
    inside a BaseService subclass for backward compatibility.
    """

    def __init__(self, model_type: type[EntityT]) -> None:
        self._model = model_type

    # ------------------------------------------------------------------
    #  Query
    # ------------------------------------------------------------------

    def get_one(
        self,
        db: Session,
        *args,  # SQLAlchemy WHERE conditions
        **kwargs,  # column=value shortcuts
    ) -> Optional[EntityT]:
        stmt = select(self._model)
        for cond in args:
            stmt = stmt.where(cond)
        for key, value in kwargs.items():
            if hasattr(self._model, key):
                stmt = stmt.where(getattr(self._model, key) == value)
        return db.exec(stmt).first()

    def get_many(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: Optional[int] = None,
        order_by: str = "id",
        desc: bool = False,
        **kwargs,  # column=value filters
    ) -> List[EntityT]:
        stmt = select(self._model)
        for key, value in kwargs.items():
            if hasattr(self._model, key):
                stmt = stmt.where(getattr(self._model, key) == value)
        if hasattr(self._model, order_by):
            col = getattr(self._model, order_by)
            stmt = stmt.order_by(col.desc() if desc else col.asc())
        if skip:
            stmt = stmt.offset(skip)
        if limit is not None:
            stmt = stmt.limit(limit)
        return list(db.exec(stmt).all())

    def count(self, db: Session, **kwargs) -> int:
        """Return count of rows matching optional column filters."""
        from sqlalchemy import func
        stmt = select(func.count()).select_from(self._model)
        for key, value in kwargs.items():
            if hasattr(self._model, key):
                stmt = stmt.where(getattr(self._model, key) == value)
        return db.exec(stmt).one()

    # ------------------------------------------------------------------
    #  Mutations
    # ------------------------------------------------------------------

    def create(
        self,
        db: Session,
        obj_in: Union[BaseModel, dict],
        *,
        commit: bool = True,
    ) -> EntityT:
        """Create and persist a row from a Pydantic model or plain dict."""
        obj_data = (
            obj_in.model_dump(exclude_unset=True)
            if hasattr(obj_in, "model_dump")
            else dict(obj_in)
        )
        db_obj = self._model(**obj_data)
        db.add(db_obj)
        if commit:
            db.commit()
            db.refresh(db_obj)
        return db_obj

    def update(
        self,
        db: Session,
        db_obj: EntityT,
        obj_in: Union[BaseModel, dict],
        *,
        commit: bool = True,
    ) -> EntityT:
        """Partial update of an existing row."""
        obj_data = (
            obj_in.model_dump(exclude_unset=True)
            if hasattr(obj_in, "model_dump")
            else dict(obj_in)
        )
        for key, value in obj_data.items():
            if hasattr(db_obj, key):
                setattr(db_obj, key, value)
        db.add(db_obj)
        if commit:
            db.commit()
            db.refresh(db_obj)
        return db_obj

    def delete(
        self,
        db: Session,
        db_obj: EntityT,
        *,
        commit: bool = True,
    ) -> EntityT:
        """Delete a row from the database."""
        db.delete(db_obj)
        if commit:
            db.commit()
        return db_obj

    # ------------------------------------------------------------------
    #  Bulk
    # ------------------------------------------------------------------

    def create_all(
        self,
        db: Session,
        objs_in: List[Union[BaseModel, dict]],
    ) -> List[EntityT]:
        """Bulk-create rows in a single transaction."""
        results: List[EntityT] = []
        for obj_in in objs_in:
            obj_data = (
                obj_in.model_dump(exclude_unset=True)
                if hasattr(obj_in, "model_dump")
                else dict(obj_in)
            )
            db_obj = self._model(**obj_data)
            db.add(db_obj)
            results.append(db_obj)
        db.commit()
        return results

    def delete_where(self, db: Session, **kwargs) -> int:
        """Delete all rows matching column filters. Returns count deleted."""
        stmt = select(self._model)
        for key, value in kwargs.items():
            if hasattr(self._model, key):
                stmt = stmt.where(getattr(self._model, key) == value)
        rows = db.exec(stmt).all()
        count = len(rows)
        for row in rows:
            db.delete(row)
        db.commit()
        return count


# ------------------------------------------------------------------
#  Backward-compatible convenience wrapper
# ------------------------------------------------------------------

class BaseService(Generic[EntityT]):
    """Service base using CRUDRepository internally.

    Keeps the familiar ``get_by_id / list_all / save / destroy``
    signatures that existing services expect, while exposing the
    full ``repo`` property for richer queries when you need them.
    """

    def __init__(self, session: Session, model_type: type[EntityT]) -> None:
        self.session = session
        self._repo = CRUDRepository(model_type)

    # -- repo access ---------------------------------------------------

    @property
    def repo(self) -> CRUDRepository[EntityT]:
        """The underlying CRUD repository for advanced queries."""
        return self._repo

    # -- convenience proxies -------------------------------------------

    def get_by_id(self, entity_id: UUID) -> Optional[EntityT]:
        return self._repo.get_one(self.session, id=entity_id)

    def list_all(self) -> List[EntityT]:
        return self._repo.get_many(self.session)

    def save(self, entity: EntityT) -> EntityT:
        """Persist (insert or merge) an entity.  If the entity carries an
        ``id`` and the row already exists it is treated as an update."""
        self.session.add(entity)
        self.session.commit()
        self.session.refresh(entity)
        return entity

    def destroy(self, entity: EntityT) -> None:
        """Remove an entity from the database."""
        self.session.delete(entity)
        self.session.commit()
