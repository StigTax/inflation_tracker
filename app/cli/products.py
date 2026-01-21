from __future__ import annotations

import argparse

from app.cli.crud_commands import (
    ArgSpec,
    CrudCommandSpec,
    TableSpec,
    register_crud_commands,
)
from app.crud import product_crud
from app.models import Product
from app.service.product import get_product
from app.service.safe_delete import delete_product


def register_product_commands(subparsers: argparse._SubParsersAction) -> None:
    spec = CrudCommandSpec(
        command='product',
        help='Управление продуктами.',
        crud=product_crud,
        model_cls=Product,
        add_args=[
            ArgSpec(
                ('name',),
                {'help': 'Название продукта.'}
            ),
            ArgSpec(
                ('-c', '--category-id'),
                {
                    'type': int,
                    'default': None,
                    'help': 'Категория продукта (ID). (опционально)'
                }
            ),
            ArgSpec(
                ('-u', '--unit-id'),
                {
                    'type': int,
                    'required': True,
                    'help': 'Единица измерения продукта (ID). (обязательно)'
                }
            ),
        ],
        update_args=[
            ArgSpec(
                ('--name',),
                {'default': None}
            ),
            ArgSpec(
                ('--category-id',),
                {'type': int, 'default': None}
            ),
            ArgSpec(
                ('--unit-id',),
                {'type': int, 'default': None}
            ),
        ],
        create_fields=('name', 'category_id', 'unit_id'),
        update_fields=('name', 'category_id', 'unit_id'),
        order_by={'id': Product.id, 'name': Product.name},
        default_order='id',
        table=TableSpec(
            columns=(
                'id',
                'name',
                'category',
                'measure_type',
                'unit'
            ),
            headers=(
                'ID',
                'Название',
                'Категория',
                'Тип',
                'Ед.'
            ),
        ),
        get_fn=lambda obj_id: get_product(product_id=obj_id),
        delete_fn=delete_product,
        refresh_after_write=True,
    )
    register_crud_commands(subparsers, spec)
