"""Сервисные операции для продуктов."""

from __future__ import annotations

import logging

from app.core.db import get_session
from app.crud import product_crud
from app.logging import logged
from app.models.product import Product


@logged(level=logging.DEBUG)
def get_product(product_id: int) -> Product:
    """Получить продукт вместе со связанными сущностями.

    Возвращает продукт, подгружая связи (категория, единица измерения),
    чтобы UI/CLI могли сразу печатать “человеческие” поля без дополнительных
    запросов.

    Args:
        product_id: ID продукта.

    Returns:
        Product: Продукт со связями.

    Raises:
        ValueError: Если продукт не найден.
    """
    with get_session() as session:
        return product_crud.get_with_relations_or_raise(
            db=session, obj_id=product_id
        )
