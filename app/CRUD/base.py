from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Generic, Optional, Type, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.validate.validators import ensure_item_exists, normalize_name

ModelT = TypeVar('ModelT')
logger = logging.getLogger(__name__)


class CRUDBase(Generic[ModelT]):
    def __init__(
        self,
        model: Type[ModelT],
    ) -> None:
        self.model = model

    def exists_by_name_ci(
        self,
        db,
        field: str,
        name: str,
        exclude_id: Optional[int] = None
    ) -> bool:
        col = getattr(self.model, field, None)
        if col is None:
            logger.warning(
                'В %s нет поля %s',
                self.model.__name__,
                field
            )
            raise AttributeError(
                f'{self.model.__name__} has no field "{field}"'
            )

        stmt = select(self.model.id, col)
        if exclude_id is not None:
            stmt = stmt.where(self.model.id != exclude_id)

        target = normalize_name(name).casefold()
        for _id, existing in db.execute(stmt):
            if isinstance(
                existing,
                str
            ) and normalize_name(existing).casefold() == target:
                return True
        return False

    def get_or_raise(
        self,
        db: Session,
        obj_id: int,
    ) -> ModelT:
        """Получение объекта по ID с проверкой существования."""
        obj = select(
            self.model,
        ).where(self.model.id == obj_id)
        obj = db.scalars(obj).first()
        ensure_item_exists(obj, self.model.__name__, obj_id)
        return obj

    def list(
        self,
        db: Session,
        *,
        offset: int = 0,
        limit: int = 100,
        order_by: Optional[Any] = None,
    ) -> list[ModelT]:
        """Получение списка объектов с пагинацией и сортировкой."""
        stmt = select(
            self.model,
        ).offset(offset).limit(limit)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        return list(db.scalars(stmt).all())

    def create(
        self,
        db: Session,
        *,
        obj_in: ModelT,
        commit: bool = True,
    ) -> ModelT:
        """Создание объекта."""
        db.add(obj_in)
        if commit:
            db.commit()
            db.refresh(obj_in)
        return obj_in

    def update(
        self,
        db: Session,
        obj_id: int,
        *,
        commit: bool = True,
        touch_updated_at: bool = True,
        **fields: Any,
    ) -> ModelT:
        """обновление объекта."""
        obj = self.get_or_raise(db, obj_id)
        for name, value in fields.items():
            if value is not None:
                setattr(obj, name, value)

        if touch_updated_at and hasattr(obj, 'to_update'):
            obj.to_update = datetime.utcnow()

        if commit:
            db.commit()
            db.refresh(obj)
        return obj

    def delete(
        self,
        db: Session,
        obj_id: int,
        *,
        commit: bool = True,
    ) -> None:
        """Удажение объекта по ID."""
        obj = self.get_or_raise(db, obj_id)
        db.delete(obj)
        if commit:
            db.commit()
