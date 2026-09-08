"""Тесты пакетного создания покупок (create_purchases_batch).

Ключевой сценарий во всех "невалидных" тестах — не просто "выброшено
исключение", а "исключение выброшено И ничего не осело в БД". Именно
это отличает пакетную вставку от цикла create_purchase() в лоб: там
первые N-1 успешных строк остались бы в базе, а тут — нет.

Важно: не открываем сессию мимо app.service.purchases (например, через
app.core.db.get_session напрямую) — conftest.py патчит get_session
именно в модулях app.service.*, а не в app.core.db.get_session
"как таковом". Прямой импорт get_session в этом файле обошёл бы патч
и упёрся бы в непроинициализированную реальную БД. Поэтому счёт ведём
через purchases.count_purchases_filtered() — он уже точно смотрит в
тестовую in-memory БД.
"""

from datetime import date

import pytest
from app.service import purchases


def test_create_purchases_batch_creates_all_rows(
    single_store, product_vegetable, product_no_category
):
    rows = [
        {'product_id': product_vegetable.id, 'quantity': 2.0, 'price': 150.0},
        {'product_id': product_no_category.id, 'quantity': 1.0, 'price': 60.0},
    ]

    created = purchases.create_purchases_batch(
        store_id=single_store.id,
        purchase_date=date(2024, 5, 1),
        rows=rows,
    )

    assert created == 2
    assert purchases.count_purchases_filtered(store_id=single_store.id) == 2


def test_batch_shares_store_and_date_across_rows(
    single_store, product_vegetable, product_no_category
):
    shared_date = date(2024, 5, 1)
    rows = [
        {'product_id': product_vegetable.id, 'quantity': 1.0, 'price': 10.0},
        {'product_id': product_no_category.id, 'quantity': 1.0, 'price': 20.0},
    ]

    purchases.create_purchases_batch(
        store_id=single_store.id, purchase_date=shared_date, rows=rows,
    )

    created = purchases.list_purchases_filtered(store_id=single_store.id)
    assert len(created) == 2
    assert all(p.store_id == single_store.id for p in created)
    assert all(p.purchase_date == shared_date for p in created)


def test_empty_rows_raises_and_creates_nothing(single_store):
    with pytest.raises(ValueError, match='Пустая партия'):
        purchases.create_purchases_batch(store_id=single_store.id, rows=[])

    assert purchases.count_purchases_filtered(store_id=single_store.id) == 0


def test_unknown_store_raises_and_creates_nothing(product_vegetable):
    with pytest.raises(ValueError):
        purchases.create_purchases_batch(
            store_id=999_999,
            rows=[{
                'product_id': product_vegetable.id,
                'quantity': 1.0,
                'price': 10.0,
            }],
        )

    assert purchases.count_purchases_filtered() == 0


def test_invalid_row_rolls_back_whole_batch(
    single_store, product_vegetable, product_no_category
):
    """Атомарность: одна невалидная строка откатывает партию целиком,
    включая уже 'успешные' строки, добавленные в сессию до неё.
    """
    rows = [
        {'product_id': product_vegetable.id, 'quantity': 1.0, 'price': 100.0},
        {
            'product_id': product_no_category.id,
            'quantity': -1.0,  # невалидно — количество не может быть <= 0
            'price': 50.0,
        },
    ]

    with pytest.raises(ValueError, match='Строка 2'):
        purchases.create_purchases_batch(store_id=single_store.id, rows=rows)

    assert purchases.count_purchases_filtered(store_id=single_store.id) == 0


def test_unknown_product_rolls_back_whole_batch(
    single_store, product_vegetable
):
    rows = [
        {'product_id': product_vegetable.id, 'quantity': 1.0, 'price': 100.0},
        {'product_id': 999_999, 'quantity': 1.0, 'price': 50.0},
    ]

    with pytest.raises(ValueError, match='Строка 2'):
        purchases.create_purchases_batch(store_id=single_store.id, rows=rows)

    assert purchases.count_purchases_filtered(store_id=single_store.id) == 0


def test_promo_fields_resolved_per_row(
    single_store, product_vegetable, product_no_category
):
    rows = [
        {
            'product_id': product_vegetable.id,
            'quantity': 1.0,
            'price': 90.0,
            'is_promo': True,
            'promo_type': 'discount',
            'regular_unit_price': 120.0,
        },
        {
            'product_id': product_no_category.id,
            'quantity': 1.0,
            'price': 50.0,
        },
    ]

    purchases.create_purchases_batch(store_id=single_store.id, rows=rows)

    by_product = {
        p.product_id: p
        for p in purchases.list_purchases_filtered(store_id=single_store.id)
    }

    promo_purchase = by_product[product_vegetable.id]
    assert promo_purchase.is_promo is True
    assert promo_purchase.promo_type == 'discount'
    assert float(promo_purchase.regular_unit_price) == pytest.approx(120.0)

    plain_purchase = by_product[product_no_category.id]
    assert plain_purchase.is_promo is False
    assert plain_purchase.promo_type is None
    assert plain_purchase.regular_unit_price is None


def test_purchase_date_defaults_to_today(single_store, product_vegetable):
    purchases.create_purchases_batch(
        store_id=single_store.id,
        rows=[{
            'product_id': product_vegetable.id,
            'quantity': 1.0,
            'price': 10.0,
        }],
    )

    [created] = purchases.list_purchases_filtered(store_id=single_store.id)
    assert created.purchase_date == date.today()


# ---------- get_last_receipt ----------
# (используется "Повторить последний чек…" в PurchasesTab)

def test_get_last_receipt_returns_none_when_no_purchases():
    assert purchases.get_last_receipt() is None


def test_get_last_receipt_returns_rows_from_most_recent_date_and_store(
    few_stores, product_vegetable, product_no_category,
):
    old_store, new_store = few_stores[0], few_stores[1]

    # Старый чек — другой магазин, другая (более ранняя) дата.
    purchases.create_purchases_batch(
        store_id=old_store.id,
        purchase_date=date(2024, 1, 1),
        rows=[{
            'product_id': product_vegetable.id,
            'quantity': 1.0,
            'price': 10.0,
        }],
    )

    # Последний чек — два товара, один магазин, одна дата.
    purchases.create_purchases_batch(
        store_id=new_store.id,
        purchase_date=date(2024, 6, 1),
        rows=[
            {
                'product_id': product_vegetable.id,
                'quantity': 2.0,
                'price': 150.0,
            },
            {
                'product_id': product_no_category.id,
                'quantity': 1.0,
                'price': 60.0,
            },
        ],
    )

    receipt = purchases.get_last_receipt()

    assert receipt['store_id'] == new_store.id
    assert receipt['purchase_date'] == date(2024, 6, 1)
    assert len(receipt['rows']) == 2
    by_product = {r['product_id']: r for r in receipt['rows']}
    assert by_product[product_vegetable.id] == {
        'product_id': product_vegetable.id,
        'quantity': 2.0,
        'price': 150.0,
    }
    assert by_product[product_no_category.id] == {
        'product_id': product_no_category.id,
        'quantity': 1.0,
        'price': 60.0,
    }


def test_get_last_receipt_ignores_older_purchases_in_same_store(
    single_store, product_vegetable, product_no_category,
):
    """Старая покупка в ТОМ ЖЕ магазине, но другой датой — не часть
    последнего чека, даже если магазин совпадает."""
    purchases.create_purchase(
        store_id=single_store.id, product_id=product_vegetable.id,
        quantity=1.0, price=10.0, purchase_date=date(2024, 1, 1),
    )
    purchases.create_purchase(
        store_id=single_store.id, product_id=product_no_category.id,
        quantity=1.0, price=20.0, purchase_date=date(2024, 6, 1),
    )

    receipt = purchases.get_last_receipt()

    assert receipt['purchase_date'] == date(2024, 6, 1)
    assert len(receipt['rows']) == 1
    assert receipt['rows'][0]['product_id'] == product_no_category.id


def test_get_last_receipt_rows_feed_directly_into_create_purchases_batch(
    single_store, product_vegetable, product_no_category,
):
    """Контракт форм: rows из get_last_receipt() должны без переделки
    подойти в rows= для create_purchases_batch()."""
    purchases.create_purchases_batch(
        store_id=single_store.id,
        purchase_date=date(2024, 6, 1),
        rows=[
            {
                'product_id': product_vegetable.id,
                'quantity': 2.0,
                'price': 150.0,
            },
        ],
    )

    receipt = purchases.get_last_receipt()

    created = purchases.create_purchases_batch(
        store_id=receipt['store_id'],
        purchase_date=date(2024, 6, 2),  # "повторяем" другим днём
        rows=receipt['rows'],
    )

    assert created == 1
    assert purchases.count_purchases_filtered(
        store_id=single_store.id
    ) == 2
