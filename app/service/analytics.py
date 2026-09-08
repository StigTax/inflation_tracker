"""Сервис аналитики и расчётов индексов."""

from __future__ import annotations

from datetime import date
from typing import Any, Literal, Optional

import pandas as pd
from sqlalchemy import func, select

from app.core.db import get_session
from app.models import Product, Purchase
from app.service.purchases import (
    list_purchases_filtered,
)

GroupBy = Literal['day', 'week', 'month', 'year']
PriceMode = Literal['paid', 'regular']
PromoMode = Literal['include', 'exclude', 'only']
ContributionBy = Literal['product', 'category']
CountBy = Literal['product', 'category', 'store']

_GROUP_TO_PERIOD = {
    'day': 'D',
    'week': 'W-MON',
    'month': 'M',
    'year': 'Y',
}


def _ensure_group_by(group_by: str) -> GroupBy:
    """Провалидировать тип группировки периода.

    Args:
        group_by: Строковый идентификатор периода
        ("day", "week", "month", "year").

    Returns:
        GroupBy: То же значение, но с типом Literal для статической типизации.

    Raises:
        ValueError: Если передано неизвестное значение.
    """
    if group_by not in {'day', 'week', 'month', 'year'}:
        raise ValueError(
            'group_by должен быть одним из: day, week, month, year')
    return group_by  # type: ignore[return-value]


def _ensure_price_mode(price_mode: str) -> PriceMode:
    """Провалидировать режим цены для расчётов.

    Args:
        price_mode: "paid" (фактически оплаченная) или "regular" (обычная).

    Returns:
        PriceMode: Валидированное значение режима.

    Raises:
        ValueError: Если режим не "paid" и не "regular".
    """
    if price_mode not in {'paid', 'regular'}:
        raise ValueError('price_mode должен быть paid или regular')
    return price_mode  # type: ignore[return-value]


def _ensure_promo_mode(promo_mode: str) -> PromoMode:
    """Провалидировать режим учёта акций.

    Args:
        promo_mode: "include" (учитывать все), "exclude" (исключить акции),
            "only" (только акции).

    Returns:
        PromoMode: Валидированное значение режима.

    Raises:
        ValueError: Если режим не входит в допустимый набор.
    """
    if promo_mode not in {'include', 'exclude', 'only'}:
        raise ValueError('promo_mode должен быть include/exclude/only')
    return promo_mode  # type: ignore[return-value]


def _period_start(dts: pd.Series, group_by: GroupBy) -> pd.Series:
    """Преобразовать список покупок в pandas.DataFrame.

    Ожидается, что объекты поддерживают `to_dict()`. Если список пустой
    или нет ключевой колонки `purchase_date`, возвращает пустой датафрейм.

    Args:
        purchases: Список объектов Purchase (или совместимых DTO).

    Returns:
        pd.DataFrame: Датафрейм по покупкам или пустой датафрейм.
    """
    dts = pd.to_datetime(dts).dt.normalize()

    if group_by == 'day':
        return dts

    if group_by == 'week':
        return dts - pd.to_timedelta(dts.dt.weekday, unit='D')

    if group_by == 'month':
        return dts.dt.to_period('M').dt.to_timestamp()

    return dts.dt.to_period('Y').dt.to_timestamp()


def _purchases_to_df(purchases: list[Any]) -> pd.DataFrame:
    """Преобразовать список покупок в pandas.DataFrame.

    Ожидается, что объекты поддерживают `to_dict()`. Если список пустой
    или нет ключевой колонки `purchase_date`, возвращает пустой датафрейм.

    Args:
        purchases: Список объектов Purchase (или совместимых DTO).

    Returns:
        pd.DataFrame: Датафрейм по покупкам или пустой датафрейм.
    """
    if not purchases:
        return pd.DataFrame()

    rows = [p.to_dict() for p in purchases]
    df = pd.DataFrame(rows)

    # minimal sanity
    if 'purchase_date' not in df.columns:
        return pd.DataFrame()

    return df


def _apply_promo_filter(
    df: pd.DataFrame,
    promo_mode: PromoMode
) -> pd.DataFrame:
    """Отфильтровать покупки по режиму учёта акций.

    - include: вернуть всё как есть
    - exclude: убрать строки, где is_promo=True
    - only: оставить только строки, где is_promo=True

    Если колонки `is_promo` нет:
    - для only возвращает пустой датафрейм,
    - иначе возвращает df без изменений.

    Args:
        df: Датафрейм покупок.
        promo_mode: Режим учёта акций.

    Returns:
        pd.DataFrame: Отфильтрованный датафрейм.
    """
    if df.empty:
        return df

    if 'is_promo' not in df.columns:
        return df.iloc[0:0] if promo_mode == 'only' else df

    promo = df['is_promo'].astype('boolean').fillna(False).astype(bool)

    if promo_mode == 'include':
        return df
    if promo_mode == 'exclude':
        return df[~promo]
    return df[promo]


def _compute_price_and_spend(
    df: pd.DataFrame,
    price_mode: PriceMode
) -> pd.DataFrame:
    """Добавить расчетные колонки цены и затрат для аналитики.

    Создаёт:
    - `unit_price_used` — цена за единицу, используемая в расчётах,
    - `spend` — затраты (= unit_price_used * quantity).

    При этом чистит данные:
    - quantity приводится к числу и фильтруется > 0;
    - цена приводится к числу и фильтруется > 0.

    Режимы:
    - paid: берёт `unit_price`
    - regular: берёт `regular_unit_price`, если есть, иначе `unit_price`

    Args:
        df: Датафрейм покупок.
        price_mode: Режим цены ("paid" или "regular").

    Returns:
        pd.DataFrame: Датафрейм с добавленными колонками или пустойv
        (если данных мало).
    """
    if df.empty:
        return df

    df = df.copy()

    if 'quantity' not in df.columns:
        return df.iloc[0:0]

    df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce')
    df = df[df['quantity'].notna() & (df['quantity'] > 0)]

    if price_mode == 'paid':
        if 'unit_price' not in df.columns:
            return df.iloc[0:0]
        df['unit_price_used'] = pd.to_numeric(
            df['unit_price'], errors='coerce')
    else:
        if 'regular_unit_price' in df.columns:
            reg = pd.to_numeric(df['regular_unit_price'], errors='coerce')
        else:
            reg = pd.Series([pd.NA] * len(df), index=df.index)

        if 'unit_price' in df.columns:
            paid = pd.to_numeric(df['unit_price'], errors='coerce')
        else:
            paid = pd.Series([pd.NA] * len(df), index=df.index)

        df['unit_price_used'] = reg.fillna(paid)

    df['unit_price_used'] = pd.to_numeric(
        df['unit_price_used'], errors='coerce')
    df = df[df['unit_price_used'].notna() & (df['unit_price_used'] > 0)]

    df['spend'] = df['unit_price_used'] * df['quantity']
    return df


def _prepare_df_for_index(
    *,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    store_id: Optional[int] = None,
    product_id: Optional[int] = None,
    product_ids: Optional[list[int]] = None,
    category_id: Optional[int] = None,
    promo_mode: PromoMode,
    price_mode: PriceMode,
    group_by: GroupBy,
) -> pd.DataFrame:
    """Собрать и подготовить датафрейм покупок для расчёта индексов.

    Делает полный пайплайн:
    1) выгружает покупки из БД через `list_purchases_filtered`;
    2) преобразует в DataFrame;
    3) применяет фильтр промо;
    4) рассчитывает unit_price_used/spend;
    5) добавляет колонку `period` (начало периода группировки);
    6) нормализует `product_id` (для индексов он обязателен).

    Оптимизация:
    - если `promo_mode == "only"`, на уровне БД ставит `is_promo=True`
    (меньше данных).

    Args:
        from_date: Начальная дата периода.
        to_date: Конечная дата периода.
        store_id: ID магазина.
        product_id: ID продукта.
        product_ids: Список ID продуктов (корзина).
        category_id: ID категории.
        promo_mode: Режим учёта акций.
        price_mode: Режим цены.
        group_by: Группировка по периоду.

    Returns:
        pd.DataFrame: Подготовленный датафрейм или пустой,
        если данных недостаточно.
    """
    is_promo_db = True if promo_mode == 'only' else None

    purchases = list_purchases_filtered(
        from_date=from_date,
        to_date=to_date,
        store_id=store_id,
        product_id=product_id,
        product_ids=product_ids,
        category_id=category_id,
        is_promo=is_promo_db,
    )
    df = _purchases_to_df(purchases)
    if df.empty:
        return df

    df = _apply_promo_filter(df, promo_mode)
    df = _compute_price_and_spend(df, price_mode)
    if df.empty:
        return df

    df['period'] = _period_start(df['purchase_date'], group_by)

    # product_id обязателен для индексов
    if 'product_id' not in df.columns:
        return df.iloc[0:0]

    df['product_id'] = pd.to_numeric(df['product_id'], errors='coerce')
    df = df[df['product_id'].notna()]
    df['product_id'] = df['product_id'].astype(int)

    return df


IndexMethod = Literal['laspeyres', 'paasche', 'fisher']


def _ensure_index_method(index_method: str) -> IndexMethod:
    """Провалидировать метод расчёта индекса цен.

    Args:
        index_method: 'laspeyres' (веса — количества базового периода),
            'paasche' (веса — количества текущего периода) или
            'fisher' (геометрическое среднее первых двух).

    Returns:
        IndexMethod: Валидированное значение.

    Raises:
        ValueError: Если метод не входит в допустимый набор.
    """
    if index_method not in {'laspeyres', 'paasche', 'fisher'}:
        raise ValueError(
            'index_method должен быть одним из: laspeyres, paasche, fisher'
        )
    return index_method  # type: ignore[return-value]


def _empty_price_index_result(
    base_period: Optional[pd.Timestamp] = None,
) -> dict[str, Any]:
    """Пустая структура результата при недостатке данных.

    Общая для всех трёх методов — раньше была продублирована три раза
    внутри _laspeyres_index на каждый ранний return.
    """
    return {
        'points': [],
        'kpi': {
            'base_period': (
                str(base_period.date()) if base_period is not None else None
            ),
            'last_period': None,
            'periods': 0,
            'items_in_base': 0,
            'items_total_base_weight': 0,
            'coverage_last': 0.0,
            'index_last': None,
            'inflation_total': None,
            'index_last_laspeyres': None,
            'index_last_paasche': None,
            'index_last_fisher': None,
        },
    }


def _compute_price_index(
    df: pd.DataFrame,
    *,
    method: IndexMethod = 'laspeyres',
    base_period: Optional[pd.Timestamp] = None,
) -> dict[str, Any]:
    """Посчитать индекс цен по корзине товаров: Ласпейрес/Пааше/Фишер.

    Три метода отличаются только тем, чьими количествами взвешивать
    цены при сравнении с базовым периодом:
    - Ласпейрес: количествами БАЗОВОГО периода
      (index = 100 * Σp_t*q0 / Σp0*q0);
    - Пааше: количествами ТЕКУЩЕГО периода (index = 100 * Σp_t*qt / Σp0*qt);
    - Фишер: их геометрическое среднее (sqrt(Ласпейрес * Пааше)).

    Поэтому вместо трёх почти одинаковых функций считаем один общий
    join (period, product) с базовым периодом и достаём из него все три
    формулы разом — гарантированно на одном и том же пересечении
    товаров (coverage), иначе сравнение методик было бы нечестным: у
    каждого метода могла бы получиться своя выборка "выживших" товаров.

    Если в текущем периоде нет части товаров из базы, индекс считается
    по пересечению доступных товаров; coverage — доля покрытого веса
    базы (по базовым тратам p0*q0 — одна и та же метрика для всех трёх
    методов, это про полноту данных, а не про формулу индекса).

    Каждая точка содержит index_laspeyres/index_paasche/index_fisher
    ОДНОВРЕМЕННО, не только выбранный method — специально для "сверки
    методик" на одних и тех же данных. `index`/`index_last` — просто
    алиас на значение выбранного method, ради обратной совместимости
    вызовов без явного метода.

    Args:
        df: Подготовленный датафрейм (с period, product_id, quantity, spend).
        method: Какое значение положить в index/index_last/inflation_total
            (остальные два всё равно считаются и возвращаются под своими
            именами).
        base_period: Базовый период; если None — берётся минимальный
            период в df.

    Returns:
        dict[str, Any]: Структура вида:
            {
              "points": [{
                    "period": "...",
                    "index": 123.4,
                    "index_laspeyres": 123.4,
                    "index_paasche": 121.9,
                    "index_fisher": 122.6,
                    "coverage": 0.9,
                    "items": 12}, ...
              ],
              "kpi": {...}
            }
    """
    if df.empty:
        return _empty_price_index_result()

    df = df.copy()
    df['period'] = pd.to_datetime(df['period'])
    df = df.sort_values('period')

    base_p = pd.to_datetime(
        base_period) if base_period is not None else df['period'].min()

    # base weights: spend in base period per product (p0*q0)
    base_slice = df[df['period'] == base_p]
    if base_slice.empty:
        return _empty_price_index_result(base_p)

    base_agg = (
        base_slice.groupby('product_id', as_index=False)
        .agg(base_qty=('quantity', 'sum'), base_spend=('spend', 'sum'))
        .copy()
    )
    base_agg = base_agg[(base_agg['base_qty'] > 0) &
                        (base_agg['base_spend'] > 0)]
    base_agg['base_price'] = base_agg['base_spend'] / base_agg['base_qty']
    base_agg['base_weight'] = base_agg['base_spend']  # p0*q0

    if base_agg.empty:
        return _empty_price_index_result(base_p)

    total_base_weight = float(base_agg['base_weight'].sum())

    per_agg = (
        df.groupby(['period', 'product_id'], as_index=False)
        .agg(qty=('quantity', 'sum'), spend=('spend', 'sum'))
        .copy()
    )
    per_agg = per_agg[(per_agg['qty'] > 0) & (per_agg['spend'] > 0)]
    per_agg['price'] = per_agg['spend'] / per_agg['qty']

    merged = per_agg.merge(
        base_agg[[
            'product_id',
            'base_price',
            'base_weight'
        ]], on='product_id', how='inner')
    merged = merged[(merged['base_price'] > 0) & (merged['price'] > 0)]

    # Ласпейрес: p_t*q0 (веса — базовые количества, зашиты в base_weight=p0*q0)
    merged['ratio'] = merged['price'] / merged['base_price']
    merged['laspeyres_num'] = merged['base_weight'] * merged['ratio']
    # Пааше: знаменатель p0*qt (числитель — это просто spend = p_t*qt)
    merged['paasche_den'] = merged['base_price'] * merged['qty']

    idx = (
        merged.groupby('period', as_index=False)
        .agg(
            laspeyres_num=('laspeyres_num', 'sum'),
            sum_w=('base_weight', 'sum'),
            paasche_num=('spend', 'sum'),
            paasche_den=('paasche_den', 'sum'),
            items=('product_id', 'nunique'),
        )
        .copy()
    )
    idx['index_laspeyres'] = 100.0 * idx['laspeyres_num'] / idx['sum_w']
    idx['index_paasche'] = 100.0 * idx['paasche_num'] / idx['paasche_den']
    idx['index_fisher'] = (
        idx['index_laspeyres'] * idx['index_paasche']
    ) ** 0.5
    idx['coverage'] = idx['sum_w'] / total_base_weight

    idx = idx.sort_values('period')

    method_col = f'index_{method}'

    points = [
        {
            'period': str(pd.Timestamp(row['period']).date()),
            'index': float(row[method_col]),
            'index_laspeyres': float(row['index_laspeyres']),
            'index_paasche': float(row['index_paasche']),
            'index_fisher': float(row['index_fisher']),
            'coverage': float(row['coverage']),
            'items': int(row['items']),
        }
        for _, row in idx.iterrows()
    ]

    last = idx.iloc[-1]
    kpi = {
        'base_period': str(pd.Timestamp(base_p).date()),
        'last_period': str(pd.Timestamp(last['period']).date()),
        'periods': int(idx.shape[0]),
        'items_in_base': int(base_agg.shape[0]),
        'items_total_base_weight': float(total_base_weight),
        'coverage_last': float(last['coverage']),
        'index_last': float(last[method_col]),
        'inflation_total': float(last[method_col] - 100.0),
        'index_last_laspeyres': float(last['index_laspeyres']),
        'index_last_paasche': float(last['index_paasche']),
        'index_last_fisher': float(last['index_fisher']),
    }

    return {'points': points, 'kpi': kpi}


def _laspeyres_index(
    df: pd.DataFrame,
    *,
    base_period: Optional[pd.Timestamp] = None,
) -> dict[str, Any]:
    """Индекс Ласпейреса — тонкая обёртка над _compute_price_index().

    Сигнатура и имя сохранены отдельно ради обратной совместимости:
    на неё напрямую завязаны существующие тесты (test_analytics.py) и
    вызовы из basket/category/store_inflation_index по умолчанию.
    """
    return _compute_price_index(
        df, method='laspeyres', base_period=base_period
    )


def _paasche_index(
    df: pd.DataFrame,
    *,
    base_period: Optional[pd.Timestamp] = None,
) -> dict[str, Any]:
    """Индекс Пааше: веса — количества ТЕКУЩЕГО периода, а не базового."""
    return _compute_price_index(
        df, method='paasche', base_period=base_period
    )


def _fisher_index(
    df: pd.DataFrame,
    *,
    base_period: Optional[pd.Timestamp] = None,
) -> dict[str, Any]:
    """Индекс Фишера: геометрическое среднее Ласпейреса и Пааше."""
    return _compute_price_index(
        df, method='fisher', base_period=base_period
    )


def purchase_counts(*, by: CountBy) -> dict[int, int]:
    """Посчитать количество покупок по сущности (для UI и быстрых подсказок).

    Args:
        by: Группировка счётчика: "product", "store" или "category".

    Returns:
        dict[int, int]: Словарь {id: count}.
    """
    with get_session() as db:
        if by == 'product':
            stmt = (
                select(Purchase.product_id, func.count(Purchase.id))
                .where(Purchase.product_id.isnot(None))
                .group_by(Purchase.product_id)
            )
        elif by == 'store':
            stmt = (
                select(Purchase.store_id, func.count(Purchase.id))
                .where(Purchase.store_id.isnot(None))
                .group_by(Purchase.store_id)
            )
        else:  # category
            stmt = (
                select(Product.category_id, func.count(Purchase.id))
                .join(Purchase.product)
                .where(Product.category_id.isnot(None))
                .group_by(Product.category_id)
            )

        rows = db.execute(stmt).all()
        return {int(k): int(v) for k, v in rows if k is not None}


def product_inflation_index(
    *,
    product_id: int,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    group_by: GroupBy = 'month',
    price_mode: PriceMode = 'paid',
    promo_mode: PromoMode = 'include',
) -> dict[str, Any]:
    """Посчитать индекс инфляции для одного продукта по периодам.

    Для каждого периода считает среднюю цену за единицу (через spend/qty),
    затем нормирует к 100 по первому периоду.

    Args:
        product_id: ID продукта.
        from_date: Начальная дата.
        to_date: Конечная дата.
        group_by: Период группировки.
        price_mode: Режим цены (paid/regular).
        promo_mode: Режим учёта акций.

    Returns:
        dict[str, Any]: {"points": [...], "kpi": {...}} или пустые структуры
        при отсутствии данных.
    """
    group_by = _ensure_group_by(group_by)
    price_mode = _ensure_price_mode(price_mode)
    promo_mode = _ensure_promo_mode(promo_mode)

    df = _prepare_df_for_index(
        from_date=from_date,
        to_date=to_date,
        product_id=product_id,
        promo_mode=promo_mode,
        price_mode=price_mode,
        group_by=group_by,
    )
    if df.empty:
        return {'points': [], 'kpi': None}

    # Для продукта нам не нужны другие товары, но на всякий случай:
    df = df[df['product_id'] == int(product_id)]
    if df.empty:
        return {'points': [], 'kpi': None}

    agg = (
        df.groupby('period', as_index=False)
        .agg(
            spend=('spend', 'sum'),
            qty=('quantity', 'sum'),
            n=('id', 'count') if 'id' in df.columns else ('quantity', 'count'),
        )
        .copy()
    )

    agg = agg[(agg['qty'] > 0) & (agg['spend'] > 0)]
    if agg.empty:
        return {'points': [], 'kpi': None}

    agg['avg_unit_price'] = agg['spend'] / agg['qty']
    agg = agg.sort_values('period')

    base_price = float(agg['avg_unit_price'].iloc[0])
    if base_price <= 0:
        return {'points': [], 'kpi': None}

    agg['index_100'] = (agg['avg_unit_price'] / base_price) * 100.0
    agg['inflation_pct_from_base'] = agg['index_100'] - 100.0

    last = agg.iloc[-1]
    prev = agg.iloc[-2] if len(agg) >= 2 else None
    mom_pct = None
    if prev is not None and float(prev['avg_unit_price']) > 0:
        mom_pct = (
            float(last['avg_unit_price']) / float(prev['avg_unit_price']) - 1.0
        ) * 100.0

    kpi = {
        'product_id': int(product_id),
        'base_period': pd.to_datetime(
            agg['period'].iloc[0]
        ).date().isoformat(),
        'base_price': base_price,
        'last_period': pd.to_datetime(last['period']).date().isoformat(),
        'last_avg_unit_price': float(last['avg_unit_price']),
        'last_index_100': float(last['index_100']),
        'change_vs_prev_period_pct': mom_pct,
        'last_n': int(last['n']),
    }

    points = agg[[
        'period',
        'avg_unit_price',
        'index_100',
        'inflation_pct_from_base',
        'n'
    ]].to_dict('records')
    for p in points:
        p['period'] = pd.to_datetime(p['period']).date().isoformat()

    return {'points': points, 'kpi': kpi}


def basket_inflation_index(
    *,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    product_ids: Optional[list[int]] = None,
    group_by: GroupBy = 'month',
    price_mode: PriceMode = 'paid',
    promo_mode: PromoMode = 'include',
    index_method: IndexMethod = 'laspeyres',
) -> dict[str, Any]:
    """Посчитать индекс инфляции по корзине выбранных продуктов.

    Args:
        from_date: Начальная дата.
        to_date: Конечная дата.
        product_ids: Список продуктов корзины.
        group_by: Период группировки.
        price_mode: Режим цены.
        promo_mode: Режим учёта акций.
        index_method: 'laspeyres' (по умолчанию), 'paasche' или 'fisher'.
            Каждая точка результата всё равно содержит все три значения
            (index_laspeyres/index_paasche/index_fisher) для сверки —
            этот параметр влияет только на то, что попадёт в index/
            index_last/inflation_total.

    Returns:
        dict[str, Any]: Точки индекса и KPI.
    """
    group_by = _ensure_group_by(group_by)
    price_mode = _ensure_price_mode(price_mode)
    promo_mode = _ensure_promo_mode(promo_mode)
    index_method = _ensure_index_method(index_method)

    df = _prepare_df_for_index(
        from_date=from_date,
        to_date=to_date,
        product_ids=product_ids,
        promo_mode=promo_mode,
        price_mode=price_mode,
        group_by=group_by,
    )
    return _compute_price_index(df, method=index_method)


def category_inflation_index(
    *,
    category_id: int,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    group_by: GroupBy = 'month',
    price_mode: PriceMode = 'paid',
    promo_mode: PromoMode = 'include',
    index_method: IndexMethod = 'laspeyres',
) -> dict[str, Any]:
    """Посчитать индекс инфляции внутри категории.

    Args:
        category_id: ID категории.
        from_date: Начальная дата.
        to_date: Конечная дата.
        group_by: Период группировки.
        price_mode: Режим цены.
        promo_mode: Режим учёта акций.
        index_method: 'laspeyres' (по умолчанию), 'paasche' или 'fisher'.

    Returns:
        dict[str, Any]: Точки индекса и KPI.
    """
    group_by = _ensure_group_by(group_by)
    price_mode = _ensure_price_mode(price_mode)
    promo_mode = _ensure_promo_mode(promo_mode)
    index_method = _ensure_index_method(index_method)

    df = _prepare_df_for_index(
        from_date=from_date,
        to_date=to_date,
        category_id=category_id,
        promo_mode=promo_mode,
        price_mode=price_mode,
        group_by=group_by,
    )
    return _compute_price_index(df, method=index_method)


def store_inflation_index(
    *,
    store_id: int,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    product_ids: Optional[list[int]] = None,
    group_by: GroupBy = 'month',
    price_mode: PriceMode = 'paid',
    promo_mode: PromoMode = 'include',
    index_method: IndexMethod = 'laspeyres',
) -> dict[str, Any]:
    """Посчитать индекс инфляции по магазину.

    Можно ограничить расчёт корзиной `product_ids`.

    Args:
        store_id: ID магазина.
        from_date: Начальная дата.
        to_date: Конечная дата.
        product_ids: Список продуктов корзины.
        group_by: Период группировки.
        price_mode: Режим цены.
        promo_mode: Режим учёта акций.
        index_method: 'laspeyres' (по умолчанию), 'paasche' или 'fisher'.

    Returns:
        dict[str, Any]: Точки индекса и KPI.
    """
    group_by = _ensure_group_by(group_by)
    price_mode = _ensure_price_mode(price_mode)
    promo_mode = _ensure_promo_mode(promo_mode)
    index_method = _ensure_index_method(index_method)

    df = _prepare_df_for_index(
        from_date=from_date,
        to_date=to_date,
        store_id=store_id,
        product_ids=product_ids,
        promo_mode=promo_mode,
        price_mode=price_mode,
        group_by=group_by,
    )
    return _compute_price_index(df, method=index_method)


def product_store_price_stats(
    *,
    product_id: int,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    price_mode: PriceMode = 'paid',
    promo_mode: PromoMode = 'include',
) -> dict[str, Any]:
    """Посчитать статистику цен по магазинам для одного продукта.

    Возвращает магазины, отсортированные по средней цене за единицу.
    Внутри каждого магазина считает min/max/avg, количество покупок и
    последнюю дату.

    Args:
        product_id: ID продукта.
        from_date: Начальная дата.
        to_date: Конечная дата.
        price_mode: Режим цены (paid/regular).
        promo_mode: Режим учёта акций.

    Returns:
        dict[str, Any]: {"points": [...], "kpi": {...}}.
    """
    price_mode = _ensure_price_mode(price_mode)
    promo_mode = _ensure_promo_mode(promo_mode)

    df = _prepare_df_for_index(
        from_date=from_date,
        to_date=to_date,
        product_id=product_id,
        promo_mode=promo_mode,
        price_mode=price_mode,
        group_by='day',
    )
    if df.empty:
        return {'points': [], 'kpi': {'product_id': product_id, 'stores': 0}}

    if 'store_id' not in df.columns:
        return {'points': [], 'kpi': {'product_id': product_id, 'stores': 0}}

    df['store_id'] = pd.to_numeric(df['store_id'], errors='coerce')
    df = df[df['store_id'].notna()]
    df['store_id'] = df['store_id'].astype(int)

    if 'store' not in df.columns:
        df['store'] = df['store_id'].astype(str)

    g = (
        df.groupby(['store_id', 'store'], as_index=False)
        .agg(
            qty=('quantity', 'sum'),
            spend=('spend', 'sum'),
            purchases=('id', 'count') if 'id' in df.columns else (
                'quantity', 'count'),
            min_price=('unit_price_used', 'min'),
            max_price=('unit_price_used', 'max'),
            last_date=('purchase_date', 'max'),
        )
        .copy()
    )
    g = g[(g['qty'] > 0) & (g['spend'] > 0)]
    g['avg_unit_price'] = g['spend'] / g['qty']
    g = g.sort_values('avg_unit_price')

    points = [
        {
            'store_id': int(r['store_id']),
            'store': r['store'],
            'avg_unit_price': float(r['avg_unit_price']),
            'min_unit_price': float(r['min_price']),
            'max_unit_price': float(r['max_price']),
            'qty': float(r['qty']),
            'purchases': int(r['purchases']),
            'last_date': str(
                pd.to_datetime(r['last_date']).date()
            ) if pd.notna(r['last_date']) else None,
        }
        for _, r in g.iterrows()
    ]

    kpi = {
        'product_id': int(product_id),
        'stores': int(g.shape[0]),
        'best_store_id': int(g.iloc[0]['store_id']) if not g.empty else None,
        'best_avg_unit_price': float(
            g.iloc[0]['avg_unit_price']
        ) if not g.empty else None,
    }
    return {'points': points, 'kpi': kpi}


def inflation_contributions(
    *,
    by: ContributionBy = 'product',
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    product_ids: Optional[list[int]] = None,
    store_id: Optional[int] = None,
    category_id: Optional[int] = None,
    group_by: GroupBy = 'month',
    price_mode: PriceMode = 'paid',
    promo_mode: PromoMode = 'include',
    top: int = 10,
) -> dict[str, Any]:
    """Посчитать вклад товаров/категорий в инфляцию относительно базового
    периода.

    Логика:
    - базовый период = первый период в данных;
    - целевой период = последний период;
    - веса = затраты базового периода (p0 * q0);
    - вклад товара в пунктах индекса (Index-100):
      share_w * (price_ratio - 1) * 100.

    Args:
        by: Группировать вклад по "product" или "category".
        from_date: Начальная дата.
        to_date: Конечная дата.
        product_ids: Корзина продуктов (если задана).
        store_id: Ограничение по магазину.
        category_id: Ограничение по категории.
        group_by: Период группировки.
        price_mode: Режим цены.
        promo_mode: Режим учёта акций.
        top: Сколько лидеров по вкладу вернуть.

    Returns:
        dict[str, Any]: {"points": [...], "kpi": {...}}.
    """
    group_by = _ensure_group_by(group_by)
    price_mode = _ensure_price_mode(price_mode)
    promo_mode = _ensure_promo_mode(promo_mode)

    df = _prepare_df_for_index(
        from_date=from_date,
        to_date=to_date,
        store_id=store_id,
        category_id=category_id,
        product_ids=product_ids,
        promo_mode=promo_mode,
        price_mode=price_mode,
        group_by=group_by,
    )
    if df.empty:
        return {
            'points': [],
            'kpi': {
                'by': by,
                'base_period': None,
                'target_period': None
            }
        }

    df['period'] = pd.to_datetime(df['period'])
    df = df.sort_values('period')
    base_p = df['period'].min()
    target_p = df['period'].max()

    base_slice = df[df['period'] == base_p]
    base_agg = (
        base_slice.groupby('product_id', as_index=False)
        .agg(base_qty=('quantity', 'sum'), base_spend=('spend', 'sum'))
        .copy()
    )
    base_agg = base_agg[(base_agg['base_qty'] > 0) &
                        (base_agg['base_spend'] > 0)]
    base_agg['base_price'] = base_agg['base_spend'] / base_agg['base_qty']
    base_agg['base_weight'] = base_agg['base_spend']

    if base_agg.empty:
        return {
            'points': [],
            'kpi': {
                'by': by,
                'base_period': str(base_p.date()),
                'target_period': str(target_p.date())
            }
        }

    # target prices
    t_slice = df[df['period'] == target_p]
    t_agg = (
        t_slice.groupby('product_id', as_index=False)
        .agg(qty=('quantity', 'sum'), spend=('spend', 'sum'))
        .copy()
    )
    t_agg = t_agg[(t_agg['qty'] > 0) & (t_agg['spend'] > 0)]
    t_agg['price'] = t_agg['spend'] / t_agg['qty']

    merged = t_agg.merge(
        base_agg[[
            'product_id',
            'base_price',
            'base_weight'
        ]], on='product_id', how='inner')
    merged = merged[(merged['base_price'] > 0) & (merged['price'] > 0)]
    if merged.empty:
        return {
            'points': [],
            'kpi': {
                'by': by,
                'base_period': str(base_p.date()),
                'target_period': str(target_p.date())
            },
        }

    merged['ratio'] = merged['price'] / merged['base_price']

    sum_w = float(merged['base_weight'].sum())
    merged['share_w'] = merged['base_weight'] / sum_w
    # вклад в пунктах индекса (Index-100) = share_w * (ratio-1) * 100
    merged['contribution'] = merged['share_w'] *\
        (merged['ratio'] - 1.0) * 100.0

    # enrich names
    names = df[['product_id', 'product']].dropna().drop_duplicates(
        'product_id') if 'product' in df.columns else None
    if names is not None and not names.empty:
        merged = merged.merge(names, on='product_id', how='left')
    else:
        merged['product'] = merged['product_id'].astype(str)

    if by == 'product':
        out = merged.sort_values(
            'contribution', ascending=False).head(max(1, int(top)))
        points = [
            {
                'product_id': int(r['product_id']),
                'product': r.get('product', None),
                'ratio': float(r['ratio']),
                'contribution': float(r['contribution']),
                'share_w': float(r['share_w']),
            }
            for _, r in out.iterrows()
        ]
        kpi = {
            'by': 'product',
            'base_period': str(base_p.date()),
            'target_period': str(target_p.date()),
            'covered_weight': float(sum_w),
        }
        return {'points': points, 'kpi': kpi}

    # by category
    # нужна привязка product -> category
    if 'category_id' in df.columns:
        cat_map = (
            df[['product_id', 'category_id', 'category']]
            .dropna(subset=['category_id'])
            .drop_duplicates('product_id')
            .copy()
        )
        cat_map['category_id'] = pd.to_numeric(
            cat_map['category_id'], errors='coerce')
        cat_map = cat_map[cat_map['category_id'].notna()]
        cat_map['category_id'] = cat_map['category_id'].astype(int)
    else:
        cat_map = pd.DataFrame(
            columns=['product_id', 'category_id', 'category'])

    merged2 = merged.merge(cat_map, on='product_id', how='left')
    merged2['category_id'] = merged2['category_id'].fillna(-1).astype(int)
    merged2['category'] = merged2['category'].fillna('UNKNOWN')

    cat = (
        merged2.groupby(['category_id', 'category'], as_index=False)
        .agg(
            contribution=('contribution', 'sum'),
            share_w=('share_w', 'sum'),
            items=('product_id', 'nunique'),
        )
        .copy()
    )
    cat = cat.sort_values(
        'contribution', ascending=False).head(max(1, int(top)))

    points = [
        {
            'category_id': int(r['category_id']),
            'category': r['category'],
            'contribution': float(r['contribution']),
            'share_w': float(r['share_w']),
            'items': int(r['items']),
        }
        for _, r in cat.iterrows()
    ]
    kpi = {
        'by': 'category',
        'base_period': str(base_p.date()),
        'target_period': str(target_p.date()),
        'covered_weight': float(sum_w),
    }
    return {'points': points, 'kpi': kpi}
