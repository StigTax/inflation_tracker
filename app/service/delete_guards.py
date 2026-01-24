'''Проверки перед удалением сущностей.'''

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Product, Purchase
from app.validate.exceptions import ObjectInUseError


def product_has_no_purchases(
    session: Session,
    product_id: int
) -> None:
    cnt = session.scalar(
        select(func.count(Purchase.id)).where(
            Purchase.product_id == product_id)
    )
    if cnt and cnt > 0:
        raise ObjectInUseError(
            f'Нельзя удалить продукт id={product_id}: '
            f'есть связанные покупки ({cnt}).'
        )


def store_has_no_purchases(
    session: Session,
    store_id: int
) -> None:
    cnt = session.scalar(
        select(func.count(Purchase.id)).where(Purchase.store_id == store_id)
    )
    if cnt and cnt > 0:
        raise ObjectInUseError(
            f'Нельзя удалить магазин id={store_id}: '
            f'есть связанные покупки ({cnt}).'
        )


def unit_has_no_products(
    session: Session,
    unit_id: int
) -> None:
    cnt = session.scalar(
        select(func.count(Product.id)).where(Product.unit_id == unit_id)
    )
    if cnt and cnt > 0:
        raise ObjectInUseError(
            f'Нельзя удалить единицу измерения id={unit_id}: '
            f'есть связанные продукты ({cnt}).'
        )


def category_has_no_products(
    session: Session,
    category_id: int
) -> None:
    cnt = session.scalar(
        select(func.count(Product.id)).where(
            Product.category_id == category_id)
    )
    if cnt and cnt > 0:
        raise ObjectInUseError(
            f'Нельзя удалить категорию id={category_id}: '
            f'есть связанные продукты ({cnt}).'
        )
