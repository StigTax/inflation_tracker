"""CLI-команды для единиц измерения."""

from __future__ import annotations

import argparse

from app.cli.crud_commands import (
    ArgSpec,
    CrudCommandSpec,
    TableSpec,
    register_crud_commands,
)
from app.crud import unit_crud
from app.models import Unit
from app.service.safe_delete import delete_unit


def register_unit_commands(subparsers: argparse._SubParsersAction) -> None:
    """Зарегистрировать CLI-команды для сущности Unit (единицы измерения).

    Регистрирует CRUD-команды для единиц измерения через
    `register_crud_commands`,
    настраивает обязательный `measure_type`,
    табличный вывод и безопасное удаление
    через `delete_unit`.

    Args:
        subparsers: Коллекция сабпарсеров верхнего уровня
        (после выбора сущности).

    Returns:
        None
    """
    spec = CrudCommandSpec(
        command='units',
        help='Управление единицами измерения (Е.И.) покупок.',
        crud=unit_crud,
        model_cls=Unit,
        add_args=[
            ArgSpec(
                ('unit',),
                {'help': 'Единица измерения (кг, л, шт и т.д.).'}
            ),
            ArgSpec(
                ('-mt', '--measure-type'),
                {
                    'required': True,
                    'help': 'Тип единицы измерения (Вес, Объем и т.д.).'
                }
            ),
        ],
        update_args=[
            ArgSpec(
                ('--unit',),
                {'default': None}
            ),
            ArgSpec(
                ('--measure-type',),
                {'default': None}
            ),
        ],
        create_fields=('unit', 'measure_type'),
        update_fields=('unit', 'measure_type'),
        order_by={'id': Unit.id, 'unit': Unit.unit},
        default_order='id',
        table=TableSpec(
            columns=('id', 'measure_type', 'unit'),
            headers=('ID', 'Тип', 'Ед.'),
        ),
        delete_fn=delete_unit,
    )
    register_crud_commands(subparsers, spec)
