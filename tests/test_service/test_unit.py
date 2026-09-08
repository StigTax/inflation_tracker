"""Тесты единиц измерения."""

import pytest
from app.crud import unit_crud
from app.models import Unit
from app.service import crud_service


def test_create_unit_rejects_case_insensitive_duplicate(unit_kg):
    with pytest.raises(ValueError, match='уже существует'):
        crud_service.create_item(
            unit_crud,
            Unit(measure_type='Вес', unit='КГ'),
        )


def test_update_unit_rejects_case_insensitive_duplicate(unit_kg, unit_l):
    with pytest.raises(ValueError, match='уже существует'):
        crud_service.update_item(unit_crud, unit_l.id, unit='КГ')


def test_update_unit_validates_measure_type_when_unit_changes(unit_l):
    with pytest.raises(ValueError, match='Тип единицы измерения'):
        crud_service.update_item(
            unit_crud,
            unit_l.id,
            unit='мл',
            measure_type='   ',
        )
