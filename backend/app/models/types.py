from enum import Enum as PyEnum
from typing import Type

from sqlalchemy import Enum as SAEnum
from sqlmodel import Column


def enum_column(enum_cls: Type[PyEnum], default=None, nullable: bool = True):
    return Column(
        SAEnum(
            enum_cls,
            values_callable=lambda e: [m.value for m in e],
            native_enum=True,
        ),
        default=default,
        nullable=nullable,
    )
