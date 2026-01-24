"""Проверки перед удалением сущностей."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Product, Purchase
from app.validate.exceptions import ObjectInUseError


def product_has_no_purchases(
    session: Session,
    product_id: int
) -> None:
    """Проверить, что у продукта нет связанных покупок.

    Используется перед удалением продукта: если покупки существуют, удаление
    запрещается.

    Args:
        session: Активная SQLAlchemy-сессия.
        product_id: ID продукта.

    Returns:
        None

    Raises:
        ObjectInUseError: Если найдены связанные покупки.
    """
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
    """Проверить, что у магазина нет связанных покупок.

    Args:
        session: Активная SQLAlchemy-сессия.
        store_id: ID магазина.

    Returns:
        None

    Raises:
        ObjectInUseError: Если найдены связанные покупки.
    """
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
    """Проверить, что единица измерения не используется продуктами.

    Args:
        session: Активная SQLAlchemy-сессия.
        unit_id: ID единицы измерения.

    Returns:
        None

    Raises:
        ObjectInUseError: Если найдены продукты, использующие эту единицу.
    """
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
    """Проверить, что категория не содержит продуктов.

    Args:
        session: Активная SQLAlchemy-сессия.
        category_id: ID категории.

    Returns:
        None

    Raises:
        ObjectInUseError: Если найдены продукты в этой категории.
    """
    cnt = session.scalar(
        select(func.count(Product.id)).where(
            Product.category_id == category_id)
    )
    if cnt and cnt > 0:
        raise ObjectInUseError(
            f'Нельзя удалить категорию id={category_id}: '
            f'есть связанные продукты ({cnt}).'
        )
