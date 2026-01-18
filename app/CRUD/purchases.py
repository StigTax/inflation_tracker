from __future__ import annotations

from typing import Optional
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Purchase, Product
from app.crud.base import CRUDBase
from app.validate.validators import ensure_item_exists


class PurchaseCRUD(CRUDBase[Purchase]):
    def __init__(self, model: type[Purchase]):
        super().__init__(model)

    def get_with_normal_attr_or_raise(
        self,
        db: Session,
        obj_id: int,
    ) -> Purchase:
        stmt = (
            select(Purchase)
            .where(Purchase.id == obj_id)
            .options(
                selectinload(Purchase.product),
                selectinload(Purchase.store),
                selectinload(Purchase.product).selectinload(Product.unit),
                selectinload(Purchase.product).selectinload(Product.category),
            )
        )
        obj = db.scalars(stmt).first()
        ensure_item_exists(obj, 'Purchase', obj_id)
        return obj

    def list(
        self,
        db: Session,
        *,
        offset=0,
        limit=100,
        order_by=None
    ) -> list[Purchase]:
        stmt = (
            select(Purchase)
            .options(
                selectinload(Purchase.product),
                selectinload(Purchase.store),
            )
            .offset(offset)
            .limit(limit)
        )
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        return list(db.scalars(stmt).all())

    def get_purchase_by_store(
        self,
        db: Session,
        store_id: int,
    ) -> list[Purchase]:
        stmt = select(Purchase).where(
            Purchase.store_id == store_id
        ).order_by(Purchase.purchase_date)
        return list(db.scalars(stmt).all())

    def get_purchase_by_product(
        self,
        db: Session,
        product_id: int,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> list[Purchase]:
        stmt = select(Purchase).where(
            Purchase.product_id == product_id
        )
        if date_from is not None:
            stmt = stmt.where(Purchase.purchase_date >= date_from)
        if date_to is not None:
            stmt = stmt.where(Purchase.purchase_date <= date_to)
        stmt = stmt.order_by(Purchase.purchase_date)
        return list(db.scalars(stmt).all())


crud = PurchaseCRUD(Purchase)
