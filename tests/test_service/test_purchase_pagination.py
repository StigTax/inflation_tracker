"""Тесты пагинации выборки покупок
(list_purchases_filtered/count_purchases_filtered).

Покрывает то, что руками проверялось при ревью, но не было закреплено
тестом:
- count_filtered() совпадает с реальным количеством под теми же
  фильтрами, что и list_filtered() — иначе GUI посчитает неверное
  число страниц;
- offset/limit режут выборку на непересекающиеся страницы, которые
  в сумме дают весь набор без потерь и дублей;
- offset/limit=None (как вызывает analytics.py) по-прежнему отдаёт
  ПОЛНУЮ выборку — это самое важное регрессионное условие всей
  затеи с пагинацией, поскольку индекс Ласпейреса считается по всем
  покупкам разом.
"""

from datetime import date, timedelta

import pytest
from app.models import Purchase
from app.service import purchases


@pytest.fixture
def many_purchases(product_vegetable, single_store):
    """30 покупок одного товара в одном магазине — на 5 больше страницы.

    Специально не кратно PURCHASES_PAGE_SIZE (25), чтобы вторая
    страница была неполной и реально проверяла граничный случай.
    """
    created = []
    for i in range(30):
        p = purchases.create_purchase(
            store_id=single_store.id,
            product_id=product_vegetable.id,
            quantity=1.0,
            price=100.0 + i,
            purchase_date=date(2024, 1, 1) + timedelta(days=i),
        )
        created.append(p)
    return created


def test_count_filtered_matches_total_created(many_purchases, single_store):
    total = purchases.count_purchases_filtered(store_id=single_store.id)
    assert total == 30


def test_list_filtered_respects_limit(many_purchases, single_store):
    page = purchases.list_purchases_filtered(
        store_id=single_store.id,
        order_by=Purchase.purchase_date.asc(),
        offset=0,
        limit=25,
    )
    assert len(page) == 25


def test_list_filtered_offset_returns_remaining_page(
    many_purchases, single_store
):
    page = purchases.list_purchases_filtered(
        store_id=single_store.id,
        order_by=Purchase.purchase_date.asc(),
        offset=25,
        limit=25,
    )
    assert len(page) == 5


def test_pages_cover_all_records_without_overlap(many_purchases, single_store):
    """Две страницы по 25 вместе дают все 30 записей без дублей."""
    order_by = Purchase.purchase_date.asc()
    page1 = purchases.list_purchases_filtered(
        store_id=single_store.id, order_by=order_by, offset=0, limit=25,
    )
    page2 = purchases.list_purchases_filtered(
        store_id=single_store.id, order_by=order_by, offset=25, limit=25,
    )

    ids_page1 = {p.id for p in page1}
    ids_page2 = {p.id for p in page2}

    assert ids_page1.isdisjoint(ids_page2)
    assert ids_page1 | ids_page2 == {p.id for p in many_purchases}


def test_no_offset_limit_returns_full_set(many_purchases, single_store):
    """Критично для analytics.py: без offset/limit — вся выборка целиком.

    analytics.py вызывает list_purchases_filtered() без пагинации,
    рассчитывая получить ВСЕ подходящие покупки для расчёта индекса.
    Если бы кто-то по ошибке проставил лимит по умолчанию — Ласпейрес
    считал бы по обрезанным данным молча, без единой ошибки в логах.
    """
    full = purchases.list_purchases_filtered(store_id=single_store.id)
    assert len(full) == 30


def test_count_matches_list_length_for_same_filters(
    many_purchases, single_store, product_vegetable
):
    """count_filtered должен совпадать с фактической длиной list_filtered
    под ТЕМИ ЖЕ фильтрами — иначе GUI покажет неверное число страниц.
    """
    total = purchases.count_purchases_filtered(
        store_id=single_store.id, product_id=product_vegetable.id,
    )
    full = purchases.list_purchases_filtered(
        store_id=single_store.id, product_id=product_vegetable.id,
    )
    assert total == len(full)


def test_count_filtered_respects_date_range(many_purchases, single_store):
    """Фильтр по датам работает в count() так же, как в list()."""
    from_date = date(2024, 1, 1)
    to_date = date(2024, 1, 10)  # дни 0..9 включительно = 10 покупок

    total = purchases.count_purchases_filtered(
        store_id=single_store.id, from_date=from_date, to_date=to_date,
    )
    assert total == 10


def test_count_filtered_zero_for_non_matching_filter(
    many_purchases, few_stores
):
    """Магазин без единой покупки — count должен быть 0, а не падать."""
    other_store = few_stores[1]
    total = purchases.count_purchases_filtered(store_id=other_store.id)
    assert total == 0
