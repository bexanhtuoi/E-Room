from typing import List, Optional, Type, TypeVar, Union
from sqlmodel import SQLModel, Session, select
from pydantic import BaseModel

ORMModel = TypeVar("ORMModel", bound=SQLModel)

class CRUDRepository:
    def __init__(self, model: Type[ORMModel]):
        self._model = model

    def get_one(self, db: Session, *args, **kwargs) -> Optional[ORMModel]:
        stmt = select(self._model)
        for condition in args:
            stmt = stmt.where(condition)
        for key, value in kwargs.items():
            if hasattr(self._model, key):
                stmt = stmt.where(getattr(self._model, key) == value)
        return db.exec(stmt).first()

    def get_many(self, db: Session, skip: int = 0, limit: int | None = None, order_by: str = "id", desc: bool = False, *args, **kwargs) -> List[ORMModel]:
        stmt = select(self._model)
        for condition in args:
            stmt = stmt.where(condition)
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
        return db.exec(stmt).all()

    def create(self, db: Session, obj_in: Union[BaseModel, dict]) -> ORMModel:
        if hasattr(obj_in, "model_dump"):
            obj_data = obj_in.model_dump(exclude_unset=True)
        else:
            obj_data = dict(obj_in)
            
        db_obj = self._model(**obj_data)

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, db_obj: ORMModel, obj_in: Union[BaseModel, dict]) -> ORMModel:
        if hasattr(obj_in, "model_dump"):
            obj_data = obj_in.model_dump(exclude_unset=True)
        else:
            obj_data = dict(obj_in)
        for key, value in obj_data.items():
            if hasattr(db_obj, key):
                setattr(db_obj, key, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, db_obj: ORMModel) -> ORMModel:
        db.delete(db_obj)
        db.commit()
        return db_obj
