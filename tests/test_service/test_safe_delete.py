"""Тесты guard-проверок при удалении (delete_guards + safe_delete)."""

import pytest
from app.crud import category_crud, product_crud, store_crud, unit_crud
from app.service import crud_service, safe_delete
from app.validate.exceptions import ObjectInUseError

# ---------- категория ----------

def test_delete_category_raises_when_has_products(
    category_food, product_vegetable,
):
    with pytest.raises(ObjectInUseError):
        safe_delete.delete_category(category_food.id)

    # категория должна остаться на месте, а не удалиться наполовину
    assert crud_service.get_item(category_crud, category_food.id) is not None


def test_delete_category_succeeds_when_empty(category_food):
    safe_delete.delete_category(category_food.id)

    with pytest.raises(ValueError):
        crud_service.get_item(category_crud, category_food.id)


# ---------- магазин ----------

def test_delete_store_raises_when_has_purchases(purchase_product, few_stores):
    store_id = few_stores[0].id

    with pytest.raises(ObjectInUseError):
        safe_delete.delete_store(store_id)

    assert crud_service.get_item(store_crud, store_id) is not None


def test_delete_store_succeeds_when_no_purchases(single_store):
    safe_delete.delete_store(single_store.id)

    with pytest.raises(ValueError):
        crud_service.get_item(store_crud, single_store.id)


# ---------- единица измерения ----------

def test_delete_unit_raises_when_has_products(product_vegetable, unit_kg):
    with pytest.raises(ObjectInUseError):
        safe_delete.delete_unit(unit_kg.id)

    assert crud_service.get_item(unit_crud, unit_kg.id) is not None


def test_delete_unit_succeeds_when_no_products(unit_l):
    safe_delete.delete_unit(unit_l.id)

    with pytest.raises(ValueError):
        crud_service.get_item(unit_crud, unit_l.id)


# ---------- продукт ----------

def test_delete_product_raises_when_has_purchases(
    purchase_product, product_vegetable,
):
    with pytest.raises(ObjectInUseError):
        safe_delete.delete_product(product_vegetable.id)

    assert crud_service.get_item(
        product_crud,
        product_vegetable.id
    ) is not None


def test_delete_product_succeeds_when_no_purchases(product_no_category):
    safe_delete.delete_product(product_no_category.id)

    with pytest.raises(ValueError):
        crud_service.get_item(product_crud, product_no_category.id)
