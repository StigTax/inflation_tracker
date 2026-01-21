from __future__ import annotations

import argparse

from app.cli.crud_commands import (
    ArgSpec,
    CrudCommandSpec,
    TableSpec,
    register_crud_commands,
)
from app.crud import category_crud
from app.models import Category
from app.service.safe_delete import delete_category


def register_category_commands(
    subparsers: argparse._SubParsersAction,
) -> None:
    spec = CrudCommandSpec(
        command='category',
        help='Управление категориями покупок.',
        crud=category_crud,
        model_cls=Category,
        add_args=[
            ArgSpec(
                ('name',),
                {'help': 'Название категории.'}
            ),
            ArgSpec(
                ('-d', '--description'),
                {'default': None, 'help': 'Описание категории.'}
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
        order_by={'id': Category.id, 'name': Category.name},
        default_order='id',
        table=TableSpec(
            columns=('id', 'name', 'description'),
            headers=('ID', 'Название', 'Описание'),
        ),
        delete_fn=delete_category,
    )
    register_crud_commands(subparsers, spec)
