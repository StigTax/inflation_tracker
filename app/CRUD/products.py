from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.crud.base import CRUDBase
from app.models import Product


class ProductCRUD(CRUDBase[Product]):
    def list(
        self,
        db: Session,
        *,
        offset: int = 0,
        limit: int = 100,
        order_by=None,
    ) -> list[Product]:
        stmt = select(Product).options(
            selectinload(Product.category),
            selectinload(Product.unit),
        )
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        stmt = stmt.offset(offset).limit(limit)
        return list(db.scalars(stmt).all())


crud = ProductCRUD(Product)
