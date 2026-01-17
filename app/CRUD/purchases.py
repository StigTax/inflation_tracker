from __future__ import annotations

from typing import Optional
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Purchase
from app.crud.base import CRUDBase


class PurchaseCRUD(CRUDBase[Purchase]):
    def __init__(self, model: type[Purchase]):
        super().__init__(model)

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
