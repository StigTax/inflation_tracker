"""Сервисные операции для покупок."""

from __future__ import annotations

import logging
from datetime import date
from typing import Any, Optional

from sqlalchemy import func, select

from app.core.db import get_session
from app.crud import product_crud, store_crud
from app.crud.purchases import crud as purchase_crud
from app.logging import logged
from app.models import Product, Purchase
from app.validate.validators import (
    validate_date_not_in_future,
    validate_date_range,
    validate_positive_value,
)


@logged(level=logging.INFO, skip_empty=True)
def create_purchase(
    *,
    store_id: int,
    product_id: int,
    quantity: float,
    price: float,
    purchase_date: Optional[date] = None,
    comment: Optional[str] = None,
    is_promo: bool = False,
    promo_type: Optional[str] = None,
    regular_unit_price: Optional[float] = None,
) -> Purchase:
    """Создать покупку с валидацией и нормализацией промо-полей.

    Правила:
    - `quantity` и `price` должны быть положительными.
    - `purchase_date` не может быть в будущем
      (если не задана — берётся “сегодня”).
    - Промо-логика:
      - `is_promo` становится True, если явно передан `is_promo=True` **или**
        задан `promo_type`/`regular_unit_price`.
      - если промо выключено, `promo_type` и `regular_unit_price` принудительно
        обнуляются (None), чтобы данные не противоречили друг другу.

    После создания возвращает покупку с подгруженными связями/нормализованными
    атрибутами через `purchase_crud.get_with_normal_attr_or_raise(...)`.

    Args:
        store_id: ID магазина.
        product_id: ID продукта.
        quantity: Количество (в единицах продукта).
        price: Итоговая стоимость покупки.
        purchase_date: Дата покупки.
        comment: Комментарий пользователя.
        is_promo: Флаг “покупка по акции”.
        promo_type: Тип акции/описание (свободный текст).
        regular_unit_price: Обычная цена за единицу (для сравнения с акцией).

    Returns:
        Purchase: Созданная покупка (со связями).

    Raises:
        ValueError: Если значения невалидны
        (неположительные числа, дата в будущем).
    """
    quantity = validate_positive_value(quantity, 'Количество товара')
    price = validate_positive_value(price, 'Стоимость товара')

    if regular_unit_price is not None:
        regular_unit_price = validate_positive_value(
            regular_unit_price, 'Обычная цена за единицу'
        )

    is_promo, promo_type, regular_unit_price = Purchase.resolve_promo(
        is_promo=is_promo,
        promo_type=promo_type,
        regular_unit_price=regular_unit_price,
        current_is_promo=False,
        current_promo_type=None,
        current_regular_unit_price=None,
    )

    purchase_date = validate_date_not_in_future(purchase_date)

    with get_session() as db:
        product_crud.get_or_raise(db=db, obj_id=product_id)
        store_crud.get_or_raise(db=db, obj_id=store_id)
        purchase = Purchase(
            store_id=store_id,
            product_id=product_id,
            quantity=quantity,
            total_price=price,
            purchase_date=purchase_date,
            comment=comment,
            is_promo=is_promo,
            promo_type=promo_type,
            regular_unit_price=regular_unit_price,
        )
        created = purchase_crud.create(db=db, obj_in=purchase, commit=True)
        return purchase_crud.get_with_normal_attr_or_raise(
            db=db,
            obj_id=created.id,
        )

@logged(level=logging.INFO, skip_empty=True)
def create_purchases_batch(
    *,
    store_id: int,
    purchase_date: Optional[date] = None,
    rows: list[dict[str, Any]],
) -> int:
    """Создать несколько покупок одним пакетом: общие дата и магазин,
    свои продукт/количество/цена (+опц. промо) на каждую строку.

    Атомарно: либо создаются ВСЕ строки партии, либо ни одной. Без
    этого, если строка №7 из десяти окажется невалидной (например,
    ссылается на уже удалённый продукт), первые шесть уже осели бы в
    БД — пользователь получил бы наполовину сохранённый чек без явного
    предупреждения, что часть товаров потерялась. Атомарность здесь не
    требует ручного BEGIN/ROLLBACK: пока не вызван db.commit(), выход
    из `with get_session()` с исключением закрывает сессию, а
    Session.close() сам откатывает все незакоммиченные db.add().

    Args:
        store_id: Общий магазин для всех строк партии.
        purchase_date: Общая дата покупки (по умолчанию — сегодня).
        rows: Список словарей вида {
            'product_id': int, 'quantity': float, 'price': float,
            'comment': Optional[str], 'is_promo': bool,
            'promo_type': Optional[str],
            'regular_unit_price': Optional[float],
        }. Ключи 'comment'/'is_promo'/'promo_type'/'regular_unit_price'
        необязательны.

    Returns:
        int: Количество созданных покупок (== len(rows)).

    Raises:
        ValueError: Если rows пуст, магазин/продукт не найден, либо
        какое-то значение невалидно — откатывает всю партию.
    """
    if not rows:
        raise ValueError('Пустая партия: нечего сохранять.')

    purchase_date = validate_date_not_in_future(purchase_date)

    with get_session() as db:
        store_crud.get_or_raise(db=db, obj_id=store_id)

        for i, row in enumerate(rows, start=1):
            try:
                product_id = row['product_id']
                quantity = validate_positive_value(
                    row['quantity'], 'Количество товара'
                )
                price = validate_positive_value(
                    row['price'], 'Стоимость товара'
                )
                regular_unit_price = row.get('regular_unit_price')
                if regular_unit_price is not None:
                    regular_unit_price = validate_positive_value(
                        regular_unit_price, 'Обычная цена за единицу'
                    )
                product_crud.get_or_raise(db=db, obj_id=product_id)
            except (ValueError, KeyError) as e:
                raise ValueError(f'Строка {i}: {e}') from e

            is_promo, promo_type, regular_unit_price = Purchase.resolve_promo(
                is_promo=row.get('is_promo', False),
                promo_type=row.get('promo_type'),
                regular_unit_price=regular_unit_price,
                current_is_promo=False,
                current_promo_type=None,
                current_regular_unit_price=None,
            )

            db.add(Purchase(
                store_id=store_id,
                product_id=product_id,
                quantity=quantity,
                total_price=price,
                purchase_date=purchase_date,
                comment=row.get('comment'),
                is_promo=is_promo,
                promo_type=promo_type,
                regular_unit_price=regular_unit_price,
            ))

        db.commit()

    return len(rows)

@logged(level=logging.INFO, skip_empty=True)
def update_purchase(
    *,
    purchase_id: int,
    store_id: Optional[int] = None,
    product_id: Optional[int] = None,
    total_price: Optional[float] = None,
    quantity: Optional[float] = None,
    comment: Optional[str] = None,
    purchase_date: Optional[date] = None,
    is_promo: Optional[bool] = None,
    promo_type: Optional[str] = None,
    regular_unit_price: Optional[float] = None,
) -> Purchase:
    """Обновить покупку с поддержкой частичного обновления и промо-логики.

    Валидирует переданные значения:
    - `total_price`, `quantity`, `regular_unit_price` должны быть
      положительными;
    - `purchase_date` не может быть в будущем.

    Промо-правила:
    - если `is_promo=False`, то `promo_type` и `regular_unit_price`
      сбрасываются в None;
    - если передан `promo_type` или `regular_unit_price`, `is_promo`
      принудительно True.

    Коммит выполняется вручную (commit=False внутри CRUD), чтобы корректно
    применить промо-правила до фиксации транзакции.

    Args:
        purchase_id: ID покупки.
        store_id: Новый ID магазина.
        product_id: Новый ID продукта.
        total_price: Новая итоговая стоимость.
        quantity: Новое количество.
        comment: Новый комментарий.
        purchase_date: Новая дата покупки.
        is_promo: Явно включить/выключить промо.
        promo_type: Тип акции/описание.
        regular_unit_price: Обычная цена за единицу.

    Returns:
        Purchase: Обновлённая покупка (со связями).

    Raises:
        ValueError: Если значения невалидны или покупка не найдена.
    """

    if total_price is not None:
        total_price = validate_positive_value(total_price, 'Стоимость товара')
    if quantity is not None:
        quantity = validate_positive_value(quantity, 'Количество товара')
    if purchase_date is not None:
        purchase_date = validate_date_not_in_future(purchase_date)
    if regular_unit_price is not None:
        regular_unit_price = validate_positive_value(
            regular_unit_price, 'Обычная цена за единицу'
        )

    with get_session() as db:
        if product_id is not None:
            product_crud.get_or_raise(db=db, obj_id=product_id)
        if store_id is not None:
            store_crud.get_or_raise(db=db, obj_id=store_id)
        purchase = purchase_crud.update(
            db=db,
            obj_id=purchase_id,
            commit=False,
            store_id=store_id,
            product_id=product_id,
            total_price=total_price,
            quantity=quantity,
            comment=comment,
            purchase_date=purchase_date,
        )

        if (
            is_promo is not None
            or promo_type is not None
            or regular_unit_price is not None
        ):
            (
                purchase.is_promo,
                purchase.promo_type,
                purchase.regular_unit_price,
            ) = Purchase.resolve_promo(
                is_promo=is_promo,
                promo_type=promo_type,
                regular_unit_price=regular_unit_price,
                current_is_promo=purchase.is_promo,
                current_promo_type=purchase.promo_type,
                current_regular_unit_price=purchase.regular_unit_price,
            )

        db.commit()
        db.refresh(purchase)
        return purchase_crud.get_with_normal_attr_or_raise(
            db=db,
            obj_id=purchase.id,
        )


@logged(level=logging.DEBUG)
def get_purchase_by_id(purchase_id: int) -> Purchase:
    """Получить покупку по ID с подгруженными связями.

    Args:
        purchase_id: ID покупки.

    Returns:
        Purchase: Покупка со связями (магазин, продукт, категория, единица).

    Raises:
        ValueError: Если покупка не найдена.
    """
    with get_session() as db:
        return purchase_crud.get_with_normal_attr_or_raise(
            db=db,
            obj_id=purchase_id,
        )


@logged(level=logging.DEBUG)
def get_purchase_by_product(
    product_id: int,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    is_promo: Optional[bool] = None,
) -> list[Purchase]:
    """Получить покупки по продукту за период.

    Даты нормализуются и проверяются через `validate_date_range(...)`.

    Args:
        product_id: ID продукта.
        from_date: Начальная дата периода.
        to_date: Конечная дата периода.
        is_promo: Фильтр по акциям (True/False) или None — без фильтра.

    Returns:
        list[Purchase]: Список покупок, отсортированный по дате.
    """
    from_date, to_date = validate_date_range(from_date, to_date)
    with get_session() as db:
        return purchase_crud.get_purchase_by_product(
            db=db,
            product_id=product_id,
            date_from=from_date,
            date_to=to_date,
            is_promo=is_promo,
        )


@logged(level=logging.DEBUG)
def get_purchase_by_store(
    store_id: int,
    is_promo: Optional[bool] = None
) -> list[Purchase]:
    """Получить покупки по магазину.

    Args:
        store_id: ID магазина.
        is_promo: Фильтр по акциям (True/False) или None — без фильтра.

    Returns:
        list[Purchase]: Список покупок, отсортированный по дате.
    """
    with get_session() as db:
        return purchase_crud.get_purchase_by_store(
            db=db,
            store_id=store_id,
            is_promo=is_promo
        )


@logged(level=logging.DEBUG)
def list_purchases(
    offset: int = 0,
    limit: int = 100,
    order_by=None,
    is_promo: Optional[bool] = None
) -> list[Purchase]:
    """Получить общий список покупок с пагинацией.

    Args:
        offset: Смещение выборки.
        limit: Максимальное количество записей.
        order_by: Сортировка (SQLAlchemy выражение/колонка).
        is_promo: Фильтр по акциям (True/False) или None — без фильтра.

    Returns:
        list[Purchase]: Список покупок.
    """
    with get_session() as db:
        return purchase_crud.list(
            db=db,
            offset=offset,
            limit=limit,
            order_by=order_by,
            is_promo=is_promo
        )


@logged(level=logging.INFO)
def delete_purchase(purchase_id: int) -> None:
    """Удалить покупку по ID.

    Args:
        purchase_id: ID покупки.

    Returns:
        None

    Raises:
        ValueError: Если покупка не найдена.
    """
    with get_session() as db:
        purchase_crud.delete(db=db, obj_id=purchase_id)


@logged(level=logging.DEBUG, skip_empty=True)
def list_purchases_filtered(
    *,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    store_id: Optional[int] = None,
    product_id: Optional[int] = None,
    product_ids: Optional[list[int]] = None,
    category_id: Optional[int] = None,
    is_promo: Optional[bool] = None,
    order_by: Optional[Any] = None,
    offset: Optional[int] = None,
    limit: Optional[int] = None,
) -> list[Purchase]:
    """Универсальная выборка покупок для аналитики и UI-фильтров.

    Поддерживает фильтрацию по:
    - диапазону дат;
    - магазину;
    - продукту или списку продуктов;
    - категории (через join с Product);
    - признаку акции.

    offset/limit по умолчанию не заданы (None) — analytics.py вызывает
    эту функцию без них и получает, как и раньше, полную отфильтрованную
    выборку целиком. Постранично выбирает только GUI (PurchasesTab),
    явно передавая offset/limit.

    Args:
        from_date: Начальная дата периода.
        to_date: Конечная дата периода.
        store_id: ID магазина.
        product_id: ID продукта.
        product_ids: Список ID продуктов (корзина/выборка).
        category_id: ID категории.
        is_promo: Фильтр по акциям (True/False) или None — без фильтра.
        order_by: Сортировка.
        offset: Смещение выборки (для пагинации).
        limit: Максимум записей (для пагинации).

    Returns:
        list[Purchase]: Список покупок, подходящих под фильтры.
    """
    from_date, to_date = validate_date_range(from_date, to_date)
    with get_session() as db:
        return purchase_crud.list_filtered(
            db=db,
            date_from=from_date,
            date_to=to_date,
            store_id=store_id,
            product_id=product_id,
            product_ids=product_ids,
            category_id=category_id,
            is_promo=is_promo,
            order_by=order_by,
            offset=offset,
            limit=limit,
        )


@logged(level=logging.DEBUG, skip_empty=True)
def count_purchases_filtered(
    *,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    store_id: Optional[int] = None,
    product_id: Optional[int] = None,
    product_ids: Optional[list[int]] = None,
    category_id: Optional[int] = None,
    is_promo: Optional[bool] = None,
) -> int:
    """Считает покупки под теми же фильтрами, что list_purchases_filtered().

    Нужно GUI для расчёта количества страниц.

    Returns:
        int: Количество подходящих покупок.
    """
    from_date, to_date = validate_date_range(from_date, to_date)
    with get_session() as db:
        return purchase_crud.count_filtered(
            db=db,
            date_from=from_date,
            date_to=to_date,
            store_id=store_id,
            product_id=product_id,
            product_ids=product_ids,
            category_id=category_id,
            is_promo=is_promo,
        )


def get_purchase_date_bounds() -> tuple[Optional[date], Optional[date]]:
    """Возвращает минимальную и максимальную дату покупок.

    Returns:
        Кортеж (min_date, max_date) по Purchase.purchase_date.
        Если покупок нет, возвращается (None, None).
    """
    with get_session() as db:
        row = db.execute(
            select(
                func.min(Purchase.purchase_date),
                func.max(Purchase.purchase_date),
            )
        ).one()
        return row[0], row[1]


@logged(level=logging.INFO, skip_empty=True)
def get_last_receipt() -> Optional[dict[str, Any]]:
    """Вернуть последний "чек" — все покупки одной датой в одном магазине.

    "Чек" здесь определяется так же, как его формирует пакетный ввод:
    общие дата и магазин, несколько товарных строк. Последним считается
    чек с максимальной purchase_date среди ВСЕХ покупок (магазин
    определяется по этой же самой свежей записи — если в один день
    покупки были в разных магазинах, берём тот, где сделана последняя
    по id запись), а не "последние N покупок подряд": иначе в чек
    могли бы затесаться товары из другого магазина или другого дня.

    Returns:
        dict вида {'store_id': int, 'purchase_date': date, 'rows': [...]}
        либо None, если ни одной покупки ещё не создано.

        Каждый элемент rows — {'product_id', 'quantity', 'price'},
        совместим с create_purchases_batch(rows=...) и с prefill
        BatchPurchaseDialog.
    """
    with get_session() as db:
        last = db.execute(
            select(Purchase.store_id, Purchase.purchase_date)
            .order_by(Purchase.purchase_date.desc(), Purchase.id.desc())
            .limit(1)
        ).first()

        if last is None:
            return None

        store_id, receipt_date = last

        rows = db.execute(
            select(Purchase)
            .where(
                Purchase.store_id == store_id,
                Purchase.purchase_date == receipt_date,
            )
            .order_by(Purchase.id.asc())
        ).scalars().all()

        return {
            'store_id': store_id,
            'purchase_date': receipt_date,
            'rows': [
                {
                    'product_id': p.product_id,
                    'quantity': float(p.quantity),
                    'price': float(p.total_price),
                }
                for p in rows
            ],
        }


@logged(level=logging.DEBUG, skip_empty=True)
def get_products_purchased_at_store(store_id: int) -> list[int]:
    """ID продуктов, которые хоть раз покупались в данном магазине.

    Нужно для GUI: при фильтрации индекса по магазину бессмысленно
    предлагать в выборе весь каталог продуктов — только те, что вообще
    когда-либо покупались именно здесь, иначе пользователь долистывает
    список из сотен товаров ради пары, что реально относятся к делу.

    Args:
        store_id: ID магазина.

    Returns:
        list[int]: ID продуктов (без дублей, порядок не гарантирован).
    """
    with get_session() as db:
        rows = db.execute(
            select(Purchase.product_id)
            .where(Purchase.store_id == store_id)
            .distinct()
        ).scalars().all()
        return [int(pid) for pid in rows if pid is not None]


def get_purchase_usage_counts() -> dict[str, dict[int, int]]:
    """Возвращает счётчики покупок для отображения в UI.

    Используется, чтобы в выпадающих списках показывать количество покупок,
    а пользователь не выбирал сущности 'на ощупь'.

    Returns:
        Словарь вида:
        {
            'products': {product_id: count},
            'stores': {store_id: count},
            'categories': {category_id: count},
        }
    """
    with get_session() as db:
        prod_rows = db.execute(
            select(Purchase.product_id, func.count(Purchase.id))
            .where(Purchase.product_id.is_not(None))
            .group_by(Purchase.product_id)
        ).all()

        store_rows = db.execute(
            select(Purchase.store_id, func.count(Purchase.id))
            .where(Purchase.store_id.is_not(None))
            .group_by(Purchase.store_id)
        ).all()

        cat_rows = db.execute(
            select(Product.category_id, func.count(Purchase.id))
            .select_from(Purchase)
            .join(Product, Product.id == Purchase.product_id)
            .where(Product.category_id.is_not(None))
            .group_by(Product.category_id)
        ).all()

    return {
        'products': {
            int(pid): int(cnt) for pid, cnt in prod_rows if pid is not None
        },
        'stores': {
            int(sid): int(cnt) for sid, cnt in store_rows if sid is not None
        },
        'categories': {
            int(cid): int(cnt) for cid, cnt in cat_rows if cid is not None
        },
    }
