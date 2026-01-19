from __future__ import annotations

from datetime import date
from typing import Optional

from app.core.db import get_session
from app.crud.purchases import crud as purchase_crud
from app.models import Purchase
from app.validate.validators import (
    validate_date_not_in_future,
    validate_positive_value,
)


def create_purchase(
    *,
    store_id: int,
    product_id: int,
    quantity: float,
    price: float,
    purchase_date: Optional[date] = None,
    comment: Optional[str] = None,
) -> Purchase:
    quantity = validate_positive_value(quantity, 'Количество товара')
    price = validate_positive_value(price, 'Стоимость товара')

    purchase_date = validate_date_not_in_future(purchase_date)
    unit_price = price / quantity

    with get_session() as db:
        purchase = Purchase(
            store_id=store_id,
            product_id=product_id,
            quantity=quantity,
            total_price=price,
            unit_price=unit_price,
            purchase_date=purchase_date,
            comment=comment,
        )
        created = purchase_crud.create(db=db, obj_in=purchase, commit=True)
        return purchase_crud.get_with_normal_attr_or_raise(
            db=db,
            obj_id=created.id,
        )


def update_purchase(
    *,
    purchase_id: int,
    store_id: Optional[int] = None,
    product_id: Optional[int] = None,
    total_price: Optional[float] = None,
    quantity: Optional[float] = None,
    comment: Optional[str] = None,
    purchase_date: Optional[date] = None,
) -> Purchase:
    need_recalc = False

    if total_price is not None:
        total_price = validate_positive_value(total_price, 'Стоимость товара')
        need_recalc = True
    if quantity is not None:
        quantity = validate_positive_value(quantity, 'Количество товара')
        need_recalc = True
    if purchase_date is not None:
        purchase_date = validate_date_not_in_future(purchase_date)

    with get_session() as db:
        purchase = purchase_crud.update(
            db=db,
            obj_id=purchase_id,
            commit=False,
            store_id=store_id,
            product_id=product_id,
            total_price=total_price,
            quantity=quantity,
            comment=comment,
            purchase_date=purchase_date,
        )

        if need_recalc:
            purchase.unit_price = purchase.total_price / purchase.quantity

        db.commit()
        db.refresh(purchase)
        return purchase_crud.get_with_normal_attr_or_raise(
            db=db,
            obj_id=purchase.id,
        )


def get_purchase_by_id(purchase_id: int) -> Purchase:
    with get_session() as db:
        return purchase_crud.get_with_normal_attr_or_raise(
            db=db,
            obj_id=purchase_id,
        )


def get_purchase_by_product(
    product_id: int,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
) -> list[Purchase]:
    with get_session() as db:
        return purchase_crud.get_purchase_by_product(
            db=db,
            product_id=product_id,
            date_from=from_date,
            date_to=to_date,
        )


def get_purchase_by_store(store_id: int) -> list[Purchase]:
    with get_session() as db:
        return purchase_crud.get_purchase_by_store(db=db, store_id=store_id)


def get_list_purchase(offset: int = 0, limit: int = 100) -> list[Purchase]:
    with get_session() as db:
        return purchase_crud.list(
            db=db,
            offset=offset,
            limit=limit,
            order_by=Purchase.purchase_date,
        )
