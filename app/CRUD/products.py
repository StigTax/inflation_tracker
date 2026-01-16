from typing import Optional
from datetime import datetime

from app.core.db import get_session
from app.models import Product


def create_product(
    name: str,
    category_id: Optional[int],
    measure_type: str,
    unit: str,
) -> Product:
    with get_session() as session:
        product = Product(
            name=name,
            category_id=category_id,
            measure_type=measure_type,
            unit=unit,
        )
        session.add(product)
        session.commit()
        session.refresh(product)
        return product


def update_product(
    product_id: int,
    *,
    name: Optional[str] = None,
    category_id: Optional[int] = None,
    measure_type: Optional[str] = None,
    unit: Optional[str] = None,
) -> Product:
    with get_session() as session:
        product = session.get(
            Product,
            product_id
        )
        if product is None:
            raise ValueError(f'Продукт {product_id} не найден')

        if name is not None:
            product.name = name
        if category_id is not None:
            product.category_id = category_id
        if measure_type is not None:
            product.measure_type = measure_type
        if unit is not None:
            product.unit = unit
        product.to_update = datetime.utcnow()
        session.commit()
        session.refresh(product)
        return product


def get_product_by_id(
    product_id: int,
) -> Optional[Product]:
    with get_session() as session:
        product = session.get(
            Product,
            product_id
        )
        return product


def get_list_product() -> list[Product]:
    with get_session() as session:
        product = session.query(Product).all()
        return product
