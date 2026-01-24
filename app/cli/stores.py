"""CLI-команды для магазинов."""

from __future__ import annotations

import argparse

from app.cli.crud_commands import (
    ArgSpec,
    CrudCommandSpec,
    TableSpec,
    register_crud_commands,
)
from app.crud import store_crud
from app.models import Store
from app.service.safe_delete import delete_store


def register_store_commands(subparsers: argparse._SubParsersAction) -> None:
    """Зарегистрировать CLI-команды для сущности Store.

    Регистрирует CRUD-команды для магазинов через `register_crud_commands`,
    добавляет аргументы для создания/обновления, табличный вывод и безопасное
    удаление через `delete_store`.

    Args:
        subparsers: Коллекция сабпарсеров верхнего уровня
        (после выбора сущности).

    Returns:
        None
    """
    spec = CrudCommandSpec(
        command='store',
        help='Управление магазинами.',
        crud=store_crud,
        model_cls=Store,
        add_args=[
            ArgSpec(
                ('name',),
                {'help': 'Название магазина.'}
            ),
            ArgSpec(
                ('-d', '--description'),
                {'default': None, 'help': 'Описание магазина.'}
            ),
        ],
        update_args=[
            ArgSpec(
                ('--name',),
                {'default': None}
            ),
            ArgSpec(
                ('--description',),
                {'default': None}
            ),
        ],
        create_fields=('name', 'description'),
        update_fields=('name', 'description'),
        order_by={'id': Store.id, 'name': Store.name},
        default_order='id',
        table=TableSpec(
            columns=('id', 'name', 'description'),
            headers=('ID', 'Название', 'Описание'),
        ),
        delete_fn=delete_store,
    )
    register_crud_commands(subparsers, spec)
