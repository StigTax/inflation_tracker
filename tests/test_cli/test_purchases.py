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
