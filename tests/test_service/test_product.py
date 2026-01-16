import pytest

from app.service import products


def test_create_product(product_vegetable, category_food):
    assert product_vegetable.id is not None
    assert product_vegetable.name == 'Огурцы'
    assert product_vegetable.category_id == category_food.id
    assert product_vegetable.measure_type == 'вес'
    assert product_vegetable.unit == 'кг'


def test_create_product_no_category(product_no_category):
    assert product_no_category.id is not None
    assert product_no_category.name == 'Вода минеральная'
    assert product_no_category.category_id is None
    assert product_no_category.measure_type == 'объем'
    assert product_no_category.unit == 'л'


def test_create_few_products(few_products, category_food):
    assert len(few_products) == 3
    assert few_products[0].name == 'Помидоры'
    assert few_products[1].name == 'Морковь'
    assert few_products[2].name == 'Капуста'


def test_update_product(product_vegetable, category_food):
    updated_product = products.update_product(
        product_vegetable.id,
        name='Огурцы свежие',
        category_id=category_food.id,
        measure_type='вес',
        unit='кг',
    )
    assert updated_product.id == product_vegetable.id
    assert updated_product.name == 'Огурцы свежие'
    assert updated_product.category_id == category_food.id
    assert updated_product.measure_type == 'вес'
    assert updated_product.unit == 'кг'


def test_get_product_by_id(product_vegetable):
    product = products.get_product_by_id(product_vegetable.id)
    assert product is not None
    assert product.id == product_vegetable.id
    assert product.name == 'Огурцы'
    assert product.category_id == product_vegetable.category_id
    assert product.measure_type == 'вес'
    assert product.unit == 'кг'


def test_get_list_product(few_products):
    product_list = products.get_list_product()
    assert len(product_list) == 3
    product_names = [product.name for product in product_list]
    assert 'Помидоры' in product_names
    assert 'Морковь' in product_names
    assert 'Капуста' in product_names
