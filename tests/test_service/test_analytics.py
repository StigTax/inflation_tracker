"""Тесты сервиса аналитики: формула Ласпейреса и индекс продукта."""

from datetime import date

import pandas as pd
import pytest
from app.crud import product_crud
from app.models import Product
from app.service import analytics, crud_service, purchases
from app.service.analytics import (
    _apply_promo_filter,
    _compute_price_and_spend,
    _ensure_index_method,
    _fisher_index,
    _laspeyres_index,
    _paasche_index,
)

# ---------- _laspeyres_index: чистая математика, без БД ----------

def test_laspeyres_index_basic_two_periods():
    df = pd.DataFrame({
        'period':     ['2024-01-01', '2024-01-01', '2024-02-01', '2024-02-01'],
        'product_id': [1, 2, 1, 2],
        'quantity':   [10, 5, 8, 5],
        'spend':      [100, 50, 96, 55],
    })

    result = _laspeyres_index(df)
    points = {p['period']: p for p in result['points']}

    assert points['2024-01-01']['index'] == pytest.approx(100.0)
    assert points['2024-01-01']['coverage'] == pytest.approx(1.0)
    assert points['2024-02-01']['index'] == pytest.approx(116.6667, rel=1e-4)
    assert points['2024-02-01']['coverage'] == pytest.approx(1.0)

    kpi = result['kpi']
    assert kpi['base_period'] == '2024-01-01'
    assert kpi['last_period'] == '2024-02-01'
    assert kpi['items_in_base'] == 2
    assert kpi['items_total_base_weight'] == pytest.approx(150.0)
    assert kpi['index_last'] == pytest.approx(116.6667, rel=1e-4)
    assert kpi['inflation_total'] == pytest.approx(16.6667, rel=1e-4)


def test_laspeyres_index_partial_coverage_when_product_disappears():
    df = pd.DataFrame({
        'period':     ['2024-01-01', '2024-01-01', '2024-02-01'],
        'product_id': [1, 2, 1],
        'quantity':   [10, 5, 8],
        'spend':      [100, 50, 96],
    })

    result = _laspeyres_index(df)
    points = {p['period']: p for p in result['points']}

    assert points['2024-02-01']['index'] == pytest.approx(120.0)
    assert points['2024-02-01']['coverage'] == pytest.approx(100 / 150)
    assert points['2024-02-01']['items'] == 1


def test_laspeyres_index_explicit_base_period_changes_direction():
    df = pd.DataFrame({
        'period':     ['2024-01-01', '2024-01-01', '2024-02-01', '2024-02-01'],
        'product_id': [1, 2, 1, 2],
        'quantity':   [10, 5, 8, 5],
        'spend':      [100, 50, 96, 55],
    })

    result = _laspeyres_index(df, base_period=pd.Timestamp('2024-02-01'))
    points = {p['period']: p for p in result['points']}

    assert points['2024-02-01']['index'] == pytest.approx(100.0)
    assert points['2024-01-01']['index'] < 100.0


def test_laspeyres_index_empty_df_returns_empty_structure():
    result = _laspeyres_index(pd.DataFrame())

    assert result['points'] == []
    assert result['kpi']['index_last'] is None
    assert result['kpi']['periods'] == 0


# ---------- _paasche_index / _fisher_index ----------

def test_paasche_equals_laspeyres_when_quantities_unchanged():
    """Если q_t == q0 для каждого товара, веса совпадают — индексы обязаны
    совпасть.

    Расхождение между Ласпейресом и Пааше — это чисто эффект смены
    структуры потребления между периодами. Без него оба метода обязаны
    дать одно и то же число, иначе где-то в реализации перепутаны
    числитель со знаменателем.
    """
    df = pd.DataFrame({
        'period':     ['2024-01-01', '2024-01-01', '2024-02-01', '2024-02-01'],
        'product_id': [1, 2, 1, 2],
        'quantity':   [10, 5, 10, 5],       # количества не меняются
        'spend':      [100, 50, 120, 55],   # меняются только цены
    })

    laspeyres = _laspeyres_index(df)
    paasche = _paasche_index(df)

    for period in ('2024-01-01', '2024-02-01'):
        l_point = next(p for p in laspeyres['points'] if p['period'] == period)
        p_point = next(p for p in paasche['points'] if p['period'] == period)
        assert l_point['index'] == pytest.approx(p_point['index'])


def test_paasche_and_fisher_diverge_from_laspeyres_when_consumption_shifts():
    """Хрестоматийный случай: спрос смещается к подешевевшему товару.

    product 1: было 10шт по 10, стало 2шт по 30 (сильно подорожал,
    стали покупать меньше). product 2: было 5шт по 10, стало 20шт по 22
    (тоже подорожал, но меньше, и стали покупать значительно больше).

    Ласпейрес (веса — старые количества, где дорогой товар 1 был
    заметной долей корзины) покажет инфляцию заметно выше, чем Пааше
    (веса — новые количества, где основную долю занимает подешевевший
    относительно товар 2) — это и есть substitution bias, ради которого
    вообще считают оба индекса.
    """
    df = pd.DataFrame({
        'period':     ['2024-01-01', '2024-01-01', '2024-02-01', '2024-02-01'],
        'product_id': [1, 2, 1, 2],
        'quantity':   [10, 5, 2, 20],
        'spend':      [100, 50, 60, 440],
    })

    laspeyres_last = _laspeyres_index(df)['points'][-1]['index']
    paasche_last = _paasche_index(df)['points'][-1]['index']
    fisher_last = _fisher_index(df)['points'][-1]['index']

    assert laspeyres_last == pytest.approx(273.3333, rel=1e-4)
    assert paasche_last == pytest.approx(227.2727, rel=1e-4)
    assert laspeyres_last > paasche_last  # классический substitution bias

    # Фишер — геометрическое, а не среднее арифметическое двух чисел
    assert fisher_last == pytest.approx(
        (laspeyres_last * paasche_last) ** 0.5, rel=1e-9
    )
    assert paasche_last < fisher_last < laspeyres_last


def test_price_index_point_always_contains_all_three_methods():
    """Любой вызов (через любую из трёх обёрток) отдаёт все три числа сразу.

    Это осознанное решение ради "сверки методик" одним запросом к БД —
    не только у выбранного через method значения, у всех трёх сразу,
    и они должны совпадать независимо от того, какую обёртку дёрнули.
    """
    df = pd.DataFrame({
        'period':     ['2024-01-01', '2024-01-01', '2024-02-01', '2024-02-01'],
        'product_id': [1, 2, 1, 2],
        'quantity':   [10, 5, 2, 20],
        'spend':      [100, 50, 60, 440],
    })

    via_laspeyres = _laspeyres_index(df)['points'][-1]
    via_paasche = _paasche_index(df)['points'][-1]
    via_fisher = _fisher_index(df)['points'][-1]

    for point in (via_laspeyres, via_paasche, via_fisher):
        assert set(
            ['index_laspeyres', 'index_paasche', 'index_fisher']
        ).issubset(point.keys())

    # index_laspeyres/index_paasche/index_fisher одинаковы независимо
    # от того, какую обёртку вызвали — отличается только алиас `index`.
    assert via_laspeyres['index_laspeyres'] == pytest.approx(
        via_paasche['index_laspeyres']
    ) == pytest.approx(via_fisher['index_laspeyres'])

    assert via_laspeyres['index'] == pytest.approx(
        via_laspeyres['index_laspeyres']
    )
    assert via_paasche['index'] == pytest.approx(via_paasche['index_paasche'])
    assert via_fisher['index'] == pytest.approx(via_fisher['index_fisher'])


def test_ensure_index_method_rejects_unknown_value():
    with pytest.raises(ValueError, match='index_method'):
        _ensure_index_method('midpoint')


def test_ensure_index_method_accepts_known_values():
    for method in ('laspeyres', 'paasche', 'fisher'):
        assert _ensure_index_method(method) == method


# ---------- _apply_promo_filter ----------

def test_apply_promo_filter_variants():
    df = pd.DataFrame({
        'is_promo': [True, False, None],
        'value': [1, 2, 3],
    })

    assert _apply_promo_filter(df, 'include')['value'].tolist() == [1, 2, 3]
    assert _apply_promo_filter(df, 'exclude')['value'].tolist() == [2, 3]
    assert _apply_promo_filter(df, 'only')['value'].tolist() == [1]


def test_apply_promo_filter_missing_column():
    df = pd.DataFrame({'value': [1, 2]})

    assert _apply_promo_filter(df, 'include')['value'].tolist() == [1, 2]
    assert _apply_promo_filter(df, 'exclude')['value'].tolist() == [1, 2]
    assert _apply_promo_filter(df, 'only').empty


# ---------- _compute_price_and_spend ----------

def test_compute_price_and_spend_regular_mode_falls_back_to_paid():
    df = pd.DataFrame({
        'quantity': [2, 2],
        'unit_price': [40, 30],
        'regular_unit_price': [50, None],
    })

    result = _compute_price_and_spend(df, 'regular')

    assert result['unit_price_used'].tolist() == pytest.approx([50, 30])
    assert result['spend'].tolist() == pytest.approx([100, 60])


def test_compute_price_and_spend_filters_invalid_rows():
    df = pd.DataFrame({
        'quantity':   [1,  0, -1, 1],
        'unit_price': [10, 10, 10, 0],
    })

    result = _compute_price_and_spend(df, 'paid')

    assert len(result) == 1
    assert result['unit_price_used'].iloc[0] == pytest.approx(10)
    assert result['spend'].iloc[0] == pytest.approx(10)


# -- product_inflation_index: интеграционные, через реальные покупки --

def test_product_inflation_index_normalizes_to_100_at_base_period(
    product_vegetable, few_stores,
):
    purchases.create_purchase(
        store_id=few_stores[0].id,
        product_id=product_vegetable.id,
        quantity=2.0,
        price=100.0,
        purchase_date=date(2024, 1, 10),
    )
    purchases.create_purchase(
        store_id=few_stores[0].id,
        product_id=product_vegetable.id,
        quantity=2.0,
        price=120.0,
        purchase_date=date(2024, 2, 10),
    )

    result = analytics.product_inflation_index(
        product_id=product_vegetable.id,
        group_by='month',
    )
    kpi = result['kpi']

    assert kpi['base_price'] == pytest.approx(50.0)
    assert kpi['last_avg_unit_price'] == pytest.approx(60.0)
    assert kpi['last_index_100'] == pytest.approx(120.0)
    assert kpi['change_vs_prev_period_pct'] == pytest.approx(20.0)

    points = result['points']
    assert len(points) == 2
    assert points[0]['index_100'] == pytest.approx(100.0)
    assert points[1]['index_100'] == pytest.approx(120.0)


def test_product_inflation_index_excludes_promo_when_requested(
    product_vegetable, few_stores,
):
    purchases.create_purchase(
        store_id=few_stores[0].id,
        product_id=product_vegetable.id,
        quantity=1.0,
        price=50.0,
        purchase_date=date(2024, 1, 5),
    )
    purchases.create_purchase(
        store_id=few_stores[0].id,
        product_id=product_vegetable.id,
        quantity=1.0,
        price=999.0,
        purchase_date=date(2024, 1, 6),
        is_promo=True,
        promo_type='clearance',
    )

    result = analytics.product_inflation_index(
        product_id=product_vegetable.id,
        group_by='month',
        promo_mode='exclude',
    )

    assert len(result['points']) == 1
    assert result['kpi']['base_price'] == pytest.approx(50.0)

def test_laspeyres_index_returns_empty_when_base_period_not_present():
    df = pd.DataFrame({
        'period': ['2024-01-01', '2024-02-01'],
        'product_id': [1, 1],
        'quantity': [10, 10],
        'spend': [100, 120],
    })

    result = _laspeyres_index(df, base_period=pd.Timestamp('2023-12-01'))

    assert result['points'] == []
    assert result['kpi']['index_last'] is None
    assert result['kpi']['base_period'] == '2023-12-01'


def test_laspeyres_index_returns_empty_when_base_period_has_no_valid_rows():
    df = pd.DataFrame({
        'period':     ['2024-01-01', '2024-01-01', '2024-02-01'],
        'product_id': [1, 2, 1],
        'quantity':   [0, 0, 10],
        'spend':      [0, 0, 120],
    })

    result = _laspeyres_index(df)

    assert result['points'] == []
    assert result['kpi']['index_last'] is None
    assert result['kpi']['base_period'] == '2024-01-01'


# ---------- фильтрация: basket / category / store ----------

def test_basket_inflation_index_restricts_to_given_products(
    product_vegetable, few_products, few_stores,
):
    other_product = few_products[0]  # Помидоры — не входит в корзину

    purchases.create_purchase(
        store_id=few_stores[0].id, product_id=product_vegetable.id,
        quantity=2.0, price=100.0, purchase_date=date(2024, 1, 10),
    )
    purchases.create_purchase(
        store_id=few_stores[0].id, product_id=product_vegetable.id,
        quantity=2.0, price=120.0, purchase_date=date(2024, 2, 10),
    )
    purchases.create_purchase(
        store_id=few_stores[0].id, product_id=other_product.id,
        quantity=1.0, price=10.0, purchase_date=date(2024, 1, 10),
    )
    purchases.create_purchase(
        store_id=few_stores[0].id, product_id=other_product.id,
        quantity=1.0, price=100.0, purchase_date=date(2024, 2, 10),
    )

    result = analytics.basket_inflation_index(
        product_ids=[product_vegetable.id], group_by='month',
    )

    assert result['kpi']['index_last'] == pytest.approx(120.0)


def test_basket_inflation_index_method_paasche_diverges_from_laspeyres(
    few_products, few_stores,
):
    """index_method реально доезжает от публичного API до формулы.

    Числа те же, что и в test_paasche_and_fisher_diverge_from_laspeyres_
    when_consumption_shifts (там — на голом датафрейме, здесь — через
    полный путь: create_purchase -> БД -> _prepare_df_for_index ->
    _compute_price_index).
    """
    product_a, product_b = few_products[0], few_products[1]

    purchases.create_purchase(
        store_id=few_stores[0].id, product_id=product_a.id,
        quantity=10.0, price=100.0, purchase_date=date(2024, 1, 10),
    )
    purchases.create_purchase(
        store_id=few_stores[0].id, product_id=product_b.id,
        quantity=5.0, price=50.0, purchase_date=date(2024, 1, 10),
    )
    purchases.create_purchase(
        store_id=few_stores[0].id, product_id=product_a.id,
        quantity=2.0, price=60.0, purchase_date=date(2024, 2, 10),
    )
    purchases.create_purchase(
        store_id=few_stores[0].id, product_id=product_b.id,
        quantity=20.0, price=440.0, purchase_date=date(2024, 2, 10),
    )

    laspeyres = analytics.basket_inflation_index(
        product_ids=[product_a.id, product_b.id], group_by='month',
    )
    paasche = analytics.basket_inflation_index(
        product_ids=[product_a.id, product_b.id], group_by='month',
        index_method='paasche',
    )
    fisher = analytics.basket_inflation_index(
        product_ids=[product_a.id, product_b.id], group_by='month',
        index_method='fisher',
    )

    assert laspeyres['kpi']['index_last'] == pytest.approx(273.3333, rel=1e-4)
    assert paasche['kpi']['index_last'] == pytest.approx(227.2727, rel=1e-4)
    assert fisher['kpi']['index_last'] == pytest.approx(
        (273.3333 * 227.2727) ** 0.5, rel=1e-3
    )

    # то же самое видно и через одинаковые index_last_* в любом из трёх
    # результатов — не только через выбранный method
    assert laspeyres['kpi']['index_last_paasche'] == pytest.approx(
        paasche['kpi']['index_last']
    )
    assert paasche['kpi']['index_last_fisher'] == pytest.approx(
        fisher['kpi']['index_last']
    )


def test_category_inflation_index_restricts_to_given_category(
    product_vegetable, category_food, few_categories, unit_kg, few_stores,
):
    other_product = crud_service.create_item(
        product_crud,
        Product(
            name='Сок яблочный',
            category_id=few_categories[0].id,
            unit_id=unit_kg.id,
        ),
    )

    purchases.create_purchase(
        store_id=few_stores[0].id, product_id=product_vegetable.id,
        quantity=2.0, price=100.0, purchase_date=date(2024, 1, 10),
    )
    purchases.create_purchase(
        store_id=few_stores[0].id, product_id=product_vegetable.id,
        quantity=2.0, price=120.0, purchase_date=date(2024, 2, 10),
    )
    purchases.create_purchase(
        store_id=few_stores[0].id, product_id=other_product.id,
        quantity=1.0, price=10.0, purchase_date=date(2024, 1, 10),
    )
    purchases.create_purchase(
        store_id=few_stores[0].id, product_id=other_product.id,
        quantity=1.0, price=100.0, purchase_date=date(2024, 2, 10),
    )

    result = analytics.category_inflation_index(
        category_id=category_food.id, group_by='month',
    )

    assert result['kpi']['index_last'] == pytest.approx(120.0)


def test_store_inflation_index_restricts_to_given_store(
    product_vegetable, few_stores,
):
    target_store, other_store = few_stores[0], few_stores[1]

    purchases.create_purchase(
        store_id=target_store.id, product_id=product_vegetable.id,
        quantity=2.0, price=100.0, purchase_date=date(2024, 1, 10),
    )
    purchases.create_purchase(
        store_id=target_store.id, product_id=product_vegetable.id,
        quantity=2.0, price=120.0, purchase_date=date(2024, 2, 10),
    )
    purchases.create_purchase(
        store_id=other_store.id, product_id=product_vegetable.id,
        quantity=1.0, price=10.0, purchase_date=date(2024, 1, 10),
    )
    purchases.create_purchase(
        store_id=other_store.id, product_id=product_vegetable.id,
        quantity=1.0, price=100.0, purchase_date=date(2024, 2, 10),
    )

    result = analytics.store_inflation_index(
        store_id=target_store.id, group_by='month',
    )

    assert result['kpi']['index_last'] == pytest.approx(120.0)


# ---------- product_store_price_stats ----------

def test_product_store_price_stats_sorts_by_avg_price_and_picks_best(
    product_vegetable, few_stores,
):
    cheap_store, expensive_store = few_stores[0], few_stores[1]

    purchases.create_purchase(
        store_id=cheap_store.id, product_id=product_vegetable.id,
        quantity=1.0, price=40.0, purchase_date=date(2024, 1, 5),
    )
    purchases.create_purchase(
        store_id=expensive_store.id, product_id=product_vegetable.id,
        quantity=1.0, price=90.0, purchase_date=date(2024, 1, 6),
    )

    result = analytics.product_store_price_stats(
        product_id=product_vegetable.id,
    )

    assert result['kpi']['stores'] == 2
    assert result['kpi']['best_store_id'] == cheap_store.id
    assert result['kpi']['best_avg_unit_price'] == pytest.approx(40.0)
    assert result['points'][0]['store_id'] == cheap_store.id


# ---------- inflation_contributions ----------

def test_inflation_contributions_by_product_ranks_top_contributor(
    product_vegetable, few_products, few_stores,
):
    other_product = few_products[0]

    purchases.create_purchase(
        store_id=few_stores[0].id, product_id=product_vegetable.id,
        quantity=1.0, price=100.0, purchase_date=date(2024, 1, 5),
    )
    purchases.create_purchase(
        store_id=few_stores[0].id, product_id=other_product.id,
        quantity=1.0, price=100.0, purchase_date=date(2024, 1, 5),
    )
    purchases.create_purchase(
        store_id=few_stores[0].id, product_id=product_vegetable.id,
        quantity=1.0, price=150.0, purchase_date=date(2024, 2, 5),
    )
    purchases.create_purchase(
        store_id=few_stores[0].id, product_id=other_product.id,
        quantity=1.0, price=100.0, purchase_date=date(2024, 2, 5),
    )

    result = analytics.inflation_contributions(
        by='product', group_by='month', top=1,
    )

    assert len(result['points']) == 1
    assert result['points'][0]['product_id'] == product_vegetable.id
    assert result['points'][0]['contribution'] == pytest.approx(25.0)


def test_inflation_contributions_by_category_aggregates_products(
    product_vegetable, few_products, few_stores, category_food,
):
    other_product = few_products[0]  # тоже в category_food

    purchases.create_purchase(
        store_id=few_stores[0].id, product_id=product_vegetable.id,
        quantity=1.0, price=100.0, purchase_date=date(2024, 1, 5),
    )
    purchases.create_purchase(
        store_id=few_stores[0].id, product_id=other_product.id,
        quantity=1.0, price=100.0, purchase_date=date(2024, 1, 5),
    )
    purchases.create_purchase(
        store_id=few_stores[0].id, product_id=product_vegetable.id,
        quantity=1.0, price=150.0, purchase_date=date(2024, 2, 5),
    )
    purchases.create_purchase(
        store_id=few_stores[0].id, product_id=other_product.id,
        quantity=1.0, price=100.0, purchase_date=date(2024, 2, 5),
    )

    result = analytics.inflation_contributions(by='category', group_by='month')

    assert len(result['points']) == 1
    assert result['points'][0]['category_id'] == category_food.id
    assert result['points'][0]['contribution'] == pytest.approx(25.0)
    assert result['points'][0]['items'] == 2


# ---------- purchase_counts ----------

def test_purchase_counts_groups_by_product(
    few_purchase_in_few_stores, product_vegetable,
):
    counts = analytics.purchase_counts(by='product')

    assert counts[product_vegetable.id] == len(few_purchase_in_few_stores)


def test_purchase_counts_groups_by_store(
    few_purchase_in_few_stores, few_stores,
):
    counts = analytics.purchase_counts(by='store')

    for store in few_stores:
        assert counts.get(store.id, 0) == 1
