from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

import pytest
from app.service import purchases


def money_div(total: float, qty: float) -> Decimal:
    return (Decimal(str(total)) / Decimal(str(qty))).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


def test_create_purchase(purchase_product, few_stores, product_vegetable):
    assert purchase_product.id is not None
    assert purchase_product.product_id == product_vegetable.id
    assert purchase_product.store_id == few_stores[0].id
    assert purchase_product.total_price == pytest.approx(150.0)
    assert purchase_product.quantity == pytest.approx(2.0)
    assert purchase_product.unit_price == money_div(150.0, 2.0)
    assert purchase_product.is_promo is False
    assert purchase_product.promo_type is None
    assert purchase_product.regular_unit_price is None


def test_update_purchase_total_price_and_quantity(purchase_product):
    updated_purchase = purchases.update_purchase(
        purchase_id=purchase_product.id,
        total_price=140.0,
        quantity=3.0,
        comment="Новый комментарий",
    )

    assert updated_purchase.id == purchase_product.id
    assert updated_purchase.total_price == pytest.approx(140.0)
    assert updated_purchase.quantity == pytest.approx(3.0)
    assert updated_purchase.unit_price == money_div(140.0, 3.0)
    assert updated_purchase.comment == "Новый комментарий"


def test_get_purchase_by_id(purchase_product):
    purchase = purchases.get_purchase_by_id(purchase_product.id)

    assert purchase is not None
    assert purchase.id == purchase_product.id
    assert purchase.store_id == purchase_product.store_id
    assert purchase.product_id == purchase_product.product_id
    assert purchase.quantity == pytest.approx(purchase_product.quantity)
    assert purchase.total_price == pytest.approx(purchase_product.total_price)
    assert purchase.unit_price == purchase_product.unit_price
    assert purchase.is_promo == purchase_product.is_promo
    assert purchase.promo_type == purchase_product.promo_type
    assert purchase.regular_unit_price == purchase_product.regular_unit_price


def test_get_list_purchase(
    few_purchase_in_few_stores, purchase_product
):
    purchase_list = purchases.list_purchases()

    assert len(purchase_list) == 4
    purchase_ids = {p.id for p in purchase_list}

    for p in few_purchase_in_few_stores:
        assert p.id in purchase_ids
    assert purchase_product.id in purchase_ids


def test_get_purchases_by_store_id(
    few_purchase_in_few_stores, few_stores
):
    store_id = few_stores[0].id

    purchases_in_store = purchases.get_purchase_by_store(store_id)
    expected_purchases = [
        p for p in few_purchase_in_few_stores if p.store_id == store_id
    ]

    assert len(purchases_in_store) == len(expected_purchases)
    purchase_ids = {p.id for p in purchases_in_store}
    for p in expected_purchases:
        assert p.id in purchase_ids


def test_get_purchases_by_product_id(
    few_purchase_in_few_stores,
    product_vegetable,
):
    product_id = product_vegetable.id

    purchases_of_product = purchases.get_purchase_by_product(product_id)
    expected_purchases = [
        p for p in few_purchase_in_few_stores if p.product_id == product_id
    ]

    assert len(purchases_of_product) == len(expected_purchases)
    purchase_ids = {p.id for p in purchases_of_product}
    for p in expected_purchases:
        assert p.id in purchase_ids


def test_get_purchases_by_product_id_with_date_filter(
    few_purchase_in_few_stores,
    product_vegetable,
):
    product_id = product_vegetable.id
    from_date = few_purchase_in_few_stores[0].purchase_date
    to_date = few_purchase_in_few_stores[1].purchase_date

    purchases_of_product = purchases.get_purchase_by_product(
        product_id,
        from_date=from_date,
        to_date=to_date,
    )
    expected_purchases = [
        p
        for p in few_purchase_in_few_stores
        if p.product_id == product_id
        and from_date <= p.purchase_date <= to_date
    ]

    assert len(purchases_of_product) == len(expected_purchases)
    purchase_ids = {p.id for p in purchases_of_product}
    for p in expected_purchases:
        assert p.id in purchase_ids


def test_update_purchase_date_in_future_raises_error(purchase_product):
    future_date = date.today() + timedelta(days=1)

    with pytest.raises(ValueError) as exc_info:
        purchases.update_purchase(
            purchase_id=purchase_product.id,
            purchase_date=future_date,
        )

    assert "в будущем" in str(exc_info.value)


def test_create_purchase_with_negative_quantity_raises_error(
    product_vegetable,
    few_stores,
):
    store = few_stores[0]

    with pytest.raises(ValueError) as exc_info:
        purchases.create_purchase(
            product_id=product_vegetable.id,
            store_id=store.id,
            quantity=-1.0,
            price=150.0,
            purchase_date=date(2024, 3, 1),
        )

    assert "Количество товара" in str(exc_info.value)


def test_create_purchase_with_zero_price_raises_error(
    product_vegetable,
    few_stores,
):
    store = few_stores[0]

    with pytest.raises(ValueError) as exc_info:
        purchases.create_purchase(
            product_id=product_vegetable.id,
            store_id=store.id,
            quantity=1.0,
            price=0.0,
            purchase_date=date(2024, 3, 1),
        )

    assert "Стоимость" in str(exc_info.value)


def test_update_purchase_set_promo_fields_turns_promo_on(purchase_product):
    updated = purchases.update_purchase(
        purchase_id=purchase_product.id,
        promo_type="discount",
        regular_unit_price=99.0,
    )

    assert updated.is_promo is True
    assert updated.promo_type == "discount"
    assert updated.regular_unit_price == pytest.approx(99.0)


def test_update_purchase_no_promo_clears_promo_fields(
    few_purchase_in_single_store
):
    # В фикстуре pur_2 должен быть промо
    promo_purchase = few_purchase_in_single_store[1]
    assert promo_purchase.is_promo is True
    assert promo_purchase.promo_type is not None

    updated = purchases.update_purchase(
        purchase_id=promo_purchase.id,
        is_promo=False,
    )

    assert updated.is_promo is False
    assert updated.promo_type is None
    assert updated.regular_unit_price is None


def test_list_purchases_filter_by_promo(
    few_purchase_in_few_stores,
    purchase_product
):
    # у нас из фикстур должен быть хотя бы 1 promo и хотя бы 1 non-promo
    all_items = purchases.list_purchases()
    promo_items = purchases.list_purchases(is_promo=True)
    non_promo_items = purchases.list_purchases(is_promo=False)

    assert len(all_items) == len(promo_items) + len(non_promo_items)
    assert all(p.is_promo for p in promo_items)
    assert all(not p.is_promo for p in non_promo_items)
