from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models import Product


class ProductCRUD(CRUDBase[Product]):
    def list(
        self,
        db: Session,
        *,
        offset=0,
        limit=100,
        order_by=None,
    ) -> list[Product]:
        stmt = select(Purchase)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        stmt = self._with_relations(stmt.offset(offset).limit(limit))
        return list(db.scalars(stmt).all())


crud = ProductCRUD(Product)
