from __future__ import annotations

from app.crud import category_crud, product_crud, store_crud, unit_crud
from app.service.crud_service import delete_item
from app.service.delete_guards import (
    category_has_no_products,
    product_has_no_purchases,
    store_has_no_purchases,
    unit_has_no_products,
)


def delete_product(product_id: int) -> None:
    delete_item(
        crud=product_crud,
        item_id=product_id,
        guards=(product_has_no_purchases,),
    )


def delete_store(store_id: int) -> None:
    delete_item(
        crud=store_crud,
        item_id=store_id,
        guards=(store_has_no_purchases,),
    )


def delete_unit(unit_id: int) -> None:
    delete_item(
        crud=unit_crud,
        item_id=unit_id,
        guards=(unit_has_no_products,),
    )


def delete_category(category_id: int) -> None:
    delete_item(
        crud=category_crud,
        item_id=category_id,
        guards=(category_has_no_products,),
    )
