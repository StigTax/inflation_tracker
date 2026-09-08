"""Тесты валидации в CLI-обработчиках покупок."""

import argparse

import pytest
from app.cli.purchases import _update


def _fake_update_args(**overrides):
    base = dict(
        id=1,
        product_id=None,
        store_id=None,
        quantity=None,
        total_price=None,
        comment=None,
        date=None,
        promo=False,
        no_promo=False,
        promo_type=None,
        regular_unit_price=None,
    )
    base.update(overrides)
    return argparse.Namespace(**base)


def test_update_rejects_promo_and_no_promo_together():
    args = _fake_update_args(promo=True, no_promo=True)

    with pytest.raises(ValueError, match='--promo и --no-promo'):
        _update(args)


def test_update_rejects_promo_type_together_with_no_promo():
    args = _fake_update_args(no_promo=True, promo_type='discount')

    with pytest.raises(ValueError, match='--no-promo'):
        _update(args)


def test_update_rejects_regular_price_together_with_no_promo():
    args = _fake_update_args(no_promo=True, regular_unit_price=99.0)

    with pytest.raises(ValueError, match='--no-promo'):
        _update(args)


def test_update_omitted_nullable_fields_are_not_forwarded(monkeypatch):
    captured = {}

    def fake_update_purchase(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(
        'app.cli.purchases.update_purchase',
        fake_update_purchase,
    )

    _update(_fake_update_args(total_price=120.0))

    assert captured['total_price'] == 120.0
    assert 'comment' not in captured
    assert 'promo_type' not in captured
    assert 'regular_unit_price' not in captured


def test_update_forwards_nullable_fields_when_value_is_provided(monkeypatch):
    captured = {}

    def fake_update_purchase(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(
        'app.cli.purchases.update_purchase',
        fake_update_purchase,
    )

    _update(
        _fake_update_args(
            comment='Комментарий',
            promo_type='discount',
            regular_unit_price=150.0,
        )
    )

    assert captured['comment'] == 'Комментарий'
    assert captured['promo_type'] == 'discount'
    assert captured['regular_unit_price'] == 150.0
