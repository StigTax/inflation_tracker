from __future__ import annotations

from typing import Any, Optional

from app.core.db import get_session
from app.models import Product
from app.crud.products import crud as product_crud


def get_product(
    product_id: int,
) -> Optional[Product]:
    with get_session() as session:
        product = product_crud.get_or_raise(
            db=session,
            obj_id=product_id,
        )
        return product


def list_products(
    offset: int = 0,
    limit: int = 100,
    order_by: Optional[Any] = None,
) -> list[Product]:
    with get_session() as session:
        products = product_crud.list(
            db=session,
            offset=offset,
            limit=limit,
            order_by=order_by,
        )
        return products


def create_product(
    product: Product,
) -> Product:
    with get_session() as session:
        product = product_crud.create(
            db=session,
            obj_in=product,
        )
        return product


def update_product(
    product_id: int,
    **fields: Any,
) -> Product:
    with get_session() as session:
        product = product_crud.update(
            db=session,
            obj_id=product_id,
            **fields,
        )
        return product


def delete_product(
    product_id: int,
) -> Product:
    with get_session() as session:
        product = product_crud.delete(
            db=session,
            obj_id=product_id,
        )
        return product
