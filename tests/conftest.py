import os
from contextlib import contextmanager
from datetime import date

import pytest
from app.core.db import Base
from app.crud import category_crud, product_crud, store_crud, unit_crud
from app.models import Category, Product, Store, Unit
from app.service import crud_service, purchases
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

DB_URL = os.getenv('TEST_DATABASE_URL', 'sqlite+pysqlite:///:memory:')


@pytest.fixture
def engine():
    engine = create_engine(
        DB_URL,
        future=True,
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
    )

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    yield engine

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(autouse=True)
def override_get_session(monkeypatch, engine):
    import app.core.db as db_module

    TestingSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
        future=True,
    )

    @contextmanager
    def _get_session():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    monkeypatch.setattr(db_module, 'get_session', _get_session)

    for mod_path in [
        'app.service.purchases',
        'app.service.crud_service',
    ]:
        try:
            mod = __import__(mod_path, fromlist=['get_session'])
            monkeypatch.setattr(mod, 'get_session', _get_session)
        except ModuleNotFoundError:
            pass


# ---------- fixtures: categories ----------
@pytest.fixture
def category_food():
    obj = Category(name='Овощи', description='Свежие овощи')
    return crud_service.create_item(category_crud, obj)


@pytest.fixture
def few_categories():
    return [
        crud_service.create_item(
            category_crud,
            Category(name='Напитки', description='Соки и воды')),
        crud_service.create_item(
            category_crud,
            Category(
                name='Молочные продукты',
                description='Свежие молочные продукты',
            ),
        ),
        crud_service.create_item(
            category_crud, Category(name='Хлебобулочные изделия')
        ),
    ]


# ---------- fixtures: stores ----------
@pytest.fixture
def single_store():
    obj = Store(name='Магнит', description='Магнит - магазин для всей семьи')
    return crud_service.create_item(store_crud, obj)


@pytest.fixture
def few_stores():
    return [
        crud_service.create_item(
            store_crud,
            Store(name='Пятерочка', description='Пятерочка выручает')
        ),
        crud_service.create_item(
            store_crud,
            Store(name='Яндекс.Лавка')
        ),
        crud_service.create_item(
            store_crud,
            Store(name='Дикси')
        ),
    ]


# ---------- fixtures: units ----------
@pytest.fixture
def unit_kg():
    return crud_service.create_item(
        unit_crud, Unit(measure_type='вес', unit='кг')
    )


@pytest.fixture
def unit_l():
    return crud_service.create_item(
        store_crud,
        Unit(measure_type='объем', unit='л')
    )


# ---------- fixtures: products ----------
@pytest.fixture
def product_vegetable(category_food, unit_kg):
    obj = Product(
        name='Огурцы',
        category_id=category_food.id,
        unit_id=unit_kg.id,
    )
    return crud_service.create_item(product_crud, obj)


@pytest.fixture
def product_no_category(unit_l):
    obj = Product(
        name='Вода минеральная',
        category_id=None,
        unit_id=unit_l.id,
    )
    return crud_service.create_item(product_crud, obj)


@pytest.fixture
def few_products(category_food, unit_kg):
    return [
        crud_service.create_item(
            product_crud,
            Product(
                name='Помидоры',
                category_id=category_food.id,
                unit_id=unit_kg.id,
            )),
        crud_service.create_item(
            product_crud,
            Product(
                name='Морковь',
                category_id=category_food.id,
                unit_id=unit_kg.id,
            )),
        crud_service.create_item(
            product_crud,
            Product(
                name='Капуста',
                category_id=category_food.id,
                unit_id=unit_kg.id,
            )),
    ]


# ---------- fixtures: purchases ----------
@pytest.fixture
def purchase_product(product_vegetable, few_stores):
    # обычная покупка (не промо) + фиксированная дата
    return purchases.create_purchase(
        store_id=few_stores[0].id,
        product_id=product_vegetable.id,
        quantity=2.0,
        price=150.0,
        purchase_date=date(2024, 1, 5),
        comment="Покупка огурцов",
        is_promo=False,
        promo_type=None,
        regular_unit_price=None,
    )


@pytest.fixture
def few_purchase_in_single_store(product_vegetable, single_store):
    # одна обычная + одна промо (чтобы покрыть новые поля)
    pur_1 = purchases.create_purchase(
        store_id=single_store.id,
        product_id=product_vegetable.id,
        quantity=1.0,
        price=80.0,
        purchase_date=date(2024, 1, 10),
        is_promo=False,
        promo_type=None,
        regular_unit_price=None,
    )
    pur_2 = purchases.create_purchase(
        store_id=single_store.id,
        product_id=product_vegetable.id,
        quantity=1.5,
        price=120.0,
        purchase_date=date(2024, 2, 15),
        is_promo=True,
        promo_type="discount",
        regular_unit_price=95.0,
    )
    return [pur_1, pur_2]


@pytest.fixture
def few_purchase_in_few_stores(product_vegetable, few_stores):
    # микс промо/не промо по разным магазинам
    pur_1 = purchases.create_purchase(
        store_id=few_stores[0].id,
        product_id=product_vegetable.id,
        quantity=2.0,
        price=150.0,
        purchase_date=date(2024, 3, 5),
        is_promo=False,
        promo_type=None,
        regular_unit_price=None,
    )
    pur_2 = purchases.create_purchase(
        store_id=few_stores[1].id,
        product_id=product_vegetable.id,
        quantity=1.0,
        price=90.0,
        purchase_date=date(2024, 3, 6),
        is_promo=True,
        promo_type="loyalty",
        regular_unit_price=105.0,
    )
    pur_3 = purchases.create_purchase(
        store_id=few_stores[2].id,
        product_id=product_vegetable.id,
        quantity=3.0,
        price=240.0,
        purchase_date=date(2024, 3, 7),
        is_promo=False,
        promo_type=None,
        regular_unit_price=None,
    )
    return [pur_1, pur_2, pur_3]
