import os
from datetime import date

import pytest

os.environ.setdefault('DB_URL', 'sqlite:///./test_db.db')

from app.core.db import Base, engine, get_session
from app.service import (
    categories, stores, products, purchases
)


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def db_session():
    with get_session() as session:
        yield session


@pytest.fixture
def category_food():
    return categories.create_category(
        name='Овощи',
        description='Свежие овощи'
    )


@pytest.fixture
def few_categories():
    cat_1 = categories.create_category(
        name='Напитки',
        description='Соки и воды'
    )
    cat_2 = categories.create_category(
        name='Молочные продукты',
        description='Свежие молочные продукты'
    )
    cat_3 = categories.create_category(
        name='Хлебобулочные изделия',
    )
    return [cat_1, cat_2, cat_3]


@pytest.fixture
def single_store():
    return stores.create_store(
        name='Магнит',
        description='Магнит - магазин для всей семьи'
    )


@pytest.fixture
def few_stores():
    store_1 = stores.create_store(
        name='Пятерочка',
        description='Пятерочка выручает'
    )
    store_2 = stores.create_store(
        name='Яндекс.Лавка',
    )
    store_3 = stores.create_store(
        name='Дикси',
    )
    return [store_1, store_2, store_3]


@pytest.fixture
def product_vegetable(category_food):
    return products.create_product(
        name='Огурцы',
        category_id=category_food.id,
        measure_type='вес',
        unit='кг',
    )

@pytest.fixture
def product_no_category():
    return products.create_product(
        name='Вода минеральная',
        category_id=None,
        measure_type='объем',
        unit='л',
    )


@pytest.fixture
def few_products(category_food):
    prod_1 = products.create_product(
        name='Помидоры',
        category_id=category_food.id,
        measure_type='вес',
        unit='кг',
    )
    prod_2 = products.create_product(
        name='Морковь',
        category_id=category_food.id,
        measure_type='вес',
        unit='кг',
    )
    prod_3 = products.create_product(
        name='Капуста',
        category_id=category_food.id,
        measure_type='вес',
        unit='кг',
    )
    return [prod_1, prod_2, prod_3]


@pytest.fixture
def purchase_product(product_vegetable, few_stores):
    return purchases.create_purchase(
        store_id=few_stores[0].id,
        product_id=product_vegetable.id,
        quantity=2.0,
        price=150.0,
        purchase_date=date.today(),
        comment='Покупка огурцов',
    )


@pytest.fixture
def few_purchase_in_single_store(
    product_vegetable, single_store
):
    pur_1 = purchases.create_purchase(
        store_id=single_store.id,
        product_id=product_vegetable.id,
        quantity=1.0,
        price=80.0,
        purchase_date=date(2024, 1, 10),
    )
    pur_2 = purchases.create_purchase(
        store_id=single_store.id,
        product_id=product_vegetable.id,
        quantity=1.5,
        price=120.0,
        purchase_date=date(2024, 2, 15),
    )
    return [pur_1, pur_2]


@pytest.fixture
def few_purchase_in_few_stores(
    product_vegetable, few_stores
):
    pur_1 = purchases.create_purchase(
        store_id=few_stores[0].id,
        product_id=product_vegetable.id,
        quantity=2.0,
        price=150.0,
        purchase_date=date(2024, 3, 5),
    )
    pur_2 = purchases.create_purchase(
        store_id=few_stores[1].id,
        product_id=product_vegetable.id,
        quantity=1.0,
        price=90.0,
        purchase_date=date(2024, 3, 6),
    )
    pur_3 = purchases.create_purchase(
        store_id=few_stores[2].id,
        product_id=product_vegetable.id,
        quantity=3.0,
        price=240.0,
        purchase_date=date(2024, 3, 7),
    )
    return [pur_1, pur_2, pur_3]


@pytest.fixture
def purchase_product_with_negative_quantity(product_vegetable, few_stores):
    return purchases.create_purchase(
        store_id=few_stores[0].id,
        product_id=product_vegetable.id,
        quantity=-1.0,
        price=90.0,
        purchase_date=date(2024, 3, 6),
    )


@pytest.fixture
def purchase_product_with_zero_price(product_vegetable, few_stores):
    return purchases.create_purchase(
        store_id=few_stores[0].id,
        product_id=product_vegetable.id,
        quantity=1.0,
        price=0.0,
        purchase_date=date(2024, 3, 6),
    )


@pytest.fixture
def purchase_product_in_future_date(
    product_vegetable, few_stores
):
    future_date = date.today().replace(year=date.today().year + 1)
    return purchases.create_purchase(
        store_id=few_stores[0].id,
        product_id=product_vegetable.id,
        quantity=1.0,
        price=90.0,
        purchase_date=future_date,
    )
