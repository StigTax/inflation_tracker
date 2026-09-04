"""CRUD-операции для продуктов."""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.crud.base import CRUDBase
from app.models import Product
from app.validate.validators import ensure_item_exists


class ProductCRUD(CRUDBase[Product]):
    def _with_relations(self, stmt):
        return stmt.options(
            selectinload(Product.category),
            selectinload(Product.unit),
        )

    def get_with_relations_or_raise(
        self,
        db: Session,
        obj_id: int
    ) -> Product:
        stmt = self._with_relations(
            select(Product).where(Product.id == obj_id)
        )
        obj = db.scalars(stmt).first()
        ensure_item_exists(obj, self.model.__name__, obj_id)
        return obj

    def list(
        self,
        db: Session,
        *,
        offset=0,
        limit=100,
        order_by=None
    ) -> list[Product]:
        stmt = select(Product)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        stmt = self._with_relations(stmt.offset(offset).limit(limit))
        return list(db.scalars(stmt).all())


crud = ProductCRUD(Product)
