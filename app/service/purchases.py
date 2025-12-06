from typing import Optional
from datetime import datetime, date

from app.core.db import get_session
from app.models import Purchase


def create_purchase(
    store_id: int,
    product_id: int,
    quantity: float,
    price: float,
    purchase_date: Optional[date] = None,
    comment: Optional[str] = None,
) -> Purchase:
    if quantity <= 0:
        raise ValueError(
            'Количество товара не может быть меньше или равной 0.'
        )
    total_price = price
    unit_price = total_price / quantity

    with get_session() as session:
        purchase = Purchase(
            store_id=store_id,
            product_id=product_id,
            quantity=quantity,
            total_price=total_price,
            unit_price=unit_price,
            purchase_date=purchase_date or date.today(),
            comment=comment,
        )
        session.add(purchase)
        session.commit()
        session.refresh(purchase)
        return purchase


def update_purchase(
    purchase_id: int,
    total_price: Optional[float] = None,
    quantity: Optional[float] = None,
    comment: Optional[str] = None,
) -> Purchase:
    with get_session() as session:
        purchase = session.get(
            Purchase,
            purchase_id
        )

        if purchase is None:
            raise ValueError(f'Покупа {purchase_id} не найдена')

        need_recalc = False
        if total_price is not None:
            purchase.total_price = total_price
            need_recalc = True
        if quantity is not None:
            if quantity <= 0:
                raise ValueError(
                    'Количество товара не может быть меньше или равна 0'
                )
            purchase.quantity = quantity
            need_recalc = True

        if comment is not None:
            purchase.comment = comment

        if need_recalc:
            purchase.unit_price = (
                purchase.total_price / purchase.quantity
            )

        session.commit()
        session.refresh(purchase)
        return purchase
