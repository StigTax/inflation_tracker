"""Сервисные операции для покупок."""

from __future__ import annotations

import logging
from datetime import date
from typing import Optional

from sqlalchemy import func, select

from app.core.db import get_session
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

    is_promo = bool(
        is_promo or promo_type is not None or regular_unit_price is not None
    )
    if not is_promo:
        promo_type = None
        regular_unit_price = None

    purchase_date = validate_date_not_in_future(purchase_date)

    with get_session() as db:
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

        if is_promo is not None:
            purchase.is_promo = is_promo
            if not is_promo:
                purchase.promo_type = None
                purchase.regular_unit_price = None

        if promo_type is not None:
            purchase.promo_type = promo_type
            purchase.is_promo = True

        if regular_unit_price is not None:
            purchase.regular_unit_price = regular_unit_price
            purchase.is_promo = True

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
) -> list[Purchase]:
    """Универсальная выборка покупок для аналитики и UI-фильтров.

    Поддерживает фильтрацию по:
    - диапазону дат;
    - магазину;
    - продукту или списку продуктов;
    - категории (через join с Product);
    - признаку акции.

    Args:
        from_date: Начальная дата периода.
        to_date: Конечная дата периода.
        store_id: ID магазина.
        product_id: ID продукта.
        product_ids: Список ID продуктов (корзина/выборка).
        category_id: ID категории.
        is_promo: Фильтр по акциям (True/False) или None — без фильтра.

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
