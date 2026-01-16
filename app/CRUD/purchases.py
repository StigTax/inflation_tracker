from typing import Optional
from datetime import datetime, date

from app.core.db import get_session
from app.models import Purchase
from app.service.validators import (
    validate_date_not_in_future, validate_positive_value
)


def create_purchase(
    store_id: int,
    product_id: int,
    quantity: float,
    price: float,
    purchase_date: Optional[date] = None,
    comment: Optional[str] = None,
) -> Purchase:
    quantity = validate_positive_value(
        quantity,
        'Количество товара'
    )
    price = validate_positive_value(
        price,
        'Стоимость товара'
    )

    unit_price = price / quantity
    purchase_date = validate_date_not_in_future(purchase_date)

    with get_session() as session:
        purchase = Purchase(
            store_id=store_id,
            product_id=product_id,
            quantity=quantity,
            total_price=price,
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
    purchase_date: Optional[date] = None,
) -> Purchase:
    with get_session() as session:
        purchase = session.get(
            Purchase,
            purchase_id
        )

        if purchase is None:
            raise ValueError(f'Покупка {purchase_id} не найдена')

        need_recalc = False
        if total_price is not None:
            total_price = validate_positive_value(
                total_price,
                'Стоимость товара'
            )
            purchase.total_price = total_price
            need_recalc = True
        if quantity is not None:
            quantity = validate_positive_value(
                quantity,
                'Количество товара'
            )
            purchase.quantity = quantity
            need_recalc = True

        if comment is not None:
            purchase.comment = comment
        
        if purchase_date is not None:
            purchase.purchase_date = validate_date_not_in_future(
                purchase_date
            )

        if need_recalc:
            purchase.unit_price = (
                purchase.total_price / purchase.quantity
            )
        purchase.to_update = datetime.utcnow()
        session.commit()
        session.refresh(purchase)
        return purchase


def get_purchase_by_id(
    purchase_id: int,
) -> Optional[Purchase]:
    with get_session() as session:
        purchase = session.get(
            Purchase,
            purchase_id
        )
        return purchase


def get_purchase_by_product(
    product_id: int,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
) -> list[Purchase]:
    with get_session() as session:
        query = session.query(Purchase).filter(
            Purchase.product_id == product_id
        )
        if from_date is not None:
            query = query.filter(Purchase.purchase_date >= from_date)
        if to_date is not None:
            query = query.filter(Purchase.purchase_date <= to_date)
        query = query.order_by(Purchase.purchase_date)
        return query.all()


def get_purchase_by_store(
    store_id: int
) -> list[Purchase]:
    with get_session() as session:
        purchases = session.query(Purchase).filter(
            Purchase.store_id == store_id
        ).order_by(Purchase.purchase_date).all()
        return purchases


def get_list_purchase() -> list[Purchase]:
    with get_session() as session:
        purchases = session.query(Purchase).order_by(
            Purchase.purchase_date
        ).all()
        return purchases
