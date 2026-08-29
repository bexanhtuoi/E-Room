from typing import List, Optional, Type, TypeVar, Union

from pydantic import BaseModel
from sqlmodel import Session, SQLModel, func, select

from app.log import db_log

ORMModel = TypeVar("ORMModel", bound=SQLModel)


class CRUDRepository:
    def __init__(self, model: Type[ORMModel]):
        self.model = model

    def get_one(self, db: Session, *args, **kwargs) -> Optional[ORMModel]:
        stmt = select(self.model)
        for condition in args:
            stmt = stmt.where(condition)
        for key, value in kwargs.items():
            if hasattr(self.model, key):
                stmt = stmt.where(getattr(self.model, key) == value)
        return db.exec(stmt).first()

    def get_many(self, db: Session, skip: int = 0, limit: int | None = None, order_by: str = "id", desc: bool = False, *args, **kwargs) -> List[ORMModel]:
        stmt = select(self.model)
        for condition in args:
            stmt = stmt.where(condition)
        for key, value in kwargs.items():
            if hasattr(self.model, key):
                stmt = stmt.where(getattr(self.model, key) == value)

        if hasattr(self.model, order_by):
            col = getattr(self.model, order_by)
            stmt = stmt.order_by(col.desc() if desc else col.asc())

        if skip:
            stmt = stmt.offset(skip)
        if limit is not None:
            stmt = stmt.limit(limit)
        return db.exec(stmt).all()

    def create(self, db: Session, obj_in: Union[BaseModel, dict]) -> ORMModel:
        if hasattr(obj_in, "model_dump"):
            obj_data = obj_in.model_dump(exclude_unset=True)
        else:
            obj_data = dict(obj_in)

        db_obj = self.model(**obj_data)

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        db_log(self.model.__tablename__, "INSERT", f"id={getattr(db_obj, 'id', '?')}")
        return db_obj

    def update(self, db: Session, db_obj: ORMModel, obj_in: Union[BaseModel, dict]) -> ORMModel:
        if hasattr(obj_in, "model_dump"):
            obj_data = obj_in.model_dump(exclude_unset=True)
        else:
            obj_data = dict(obj_in)
        changed_keys = list(obj_data.keys())
        for key, value in obj_data.items():
            if hasattr(db_obj, key):
                setattr(db_obj, key, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        db_log(self.model.__tablename__, "UPDATE", f"id={getattr(db_obj, 'id', '?')} fields={changed_keys}")
        return db_obj

    def delete(self, db: Session, db_obj: ORMModel) -> ORMModel:
        obj_id = getattr(db_obj, "id", "?")
        db.delete(db_obj)
        db.commit()
        db_log(self.model.__tablename__, "DELETE", f"id={obj_id}")
        return db_obj

    def count(self, db: Session, *args, **kwargs) -> int:
        stmt = select(func.count()).select_from(self.model)
        for condition in args:
            stmt = stmt.where(condition)
        for key, value in kwargs.items():
            if hasattr(self.model, key):
                stmt = stmt.where(getattr(self.model, key) == value)
        return db.exec(stmt).one()
