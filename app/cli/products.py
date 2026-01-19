from __future__ import annotations

import argparse

from app.cli.common import (
    add_list_args,
    print_item,
    print_list_items,
    print_list_verbose,
    print_table,
)
from app.core.db import session_scope
from app.crud.products import crud as product_crud
from app.models import Product


def register_product_commands(subparsers: argparse._SubParsersAction) -> None:
    pars = subparsers.add_parser(
        'product',
        help='Управление продуктами.',
    )
    subpars = pars.add_subparsers(dest='action', required=True)

    add = subpars.add_parser('add', help='Добавить продукт.')
    add.add_argument('name', help='Название продукта.')
    add.add_argument(
        '-c',
        '--category-id',
        type=int,
        default=None,
        help='Категория продукта (ID). (опционально)',
    )
    add.add_argument(
        '-u',
        '--unit-id',
        type=int,
        required=True,
        help='Единица измерения продукта (ID). (обязательно)',
    )
    add.set_defaults(func=cmd_add)

    lst = subpars.add_parser('list', help='Список продуктов')
    grp = lst.add_mutually_exclusive_group()
    grp.add_argument('--full', action='store_true',
                     help='key: value для каждого объекта')
    grp.add_argument('--table', action='store_true', help='табличный вывод')
    add_list_args(
        lst,
        order_choices=('id', 'name'),
        default_order='id',
    )
    lst.set_defaults(func=cmd_list)

    get = subpars.add_parser('get', help='Получить продукт по id')
    get.add_argument('id', type=int)
    get.set_defaults(func=cmd_get)

    upd = subpars.add_parser('update', help='Обновить продукт')
    upd.add_argument('id', type=int)
    upd.add_argument('--name', default=None)
    upd.add_argument('--category-id', default=None, type=int)
    upd.add_argument('--unit-id', default=None, type=int)
    upd.set_defaults(func=cmd_update)

    rm = subpars.add_parser('delete', help='Удалить продукт')
    rm.add_argument('id', type=int)
    rm.set_defaults(func=cmd_delete)


def cmd_add(args: argparse.Namespace) -> None:
    with session_scope() as db:
        obj = Product(
            name=args.name,
            category_id=args.category_id,
            unit_id=args.unit_id,
        )
        obj = product_crud.create(db=db, obj_in=obj, commit=True)
        print_item(obj)


def cmd_list(args: argparse.Namespace) -> None:
    with session_scope() as db:
        order_col = Product.id if args.order == 'id' else Product.name
        items = product_crud.list(
            db=db, offset=args.offset, limit=args.limit, order_by=order_col,
        )

        if args.table:
            print_table(
                items,
                columns=('id', 'name', 'category', 'measure_type', 'unit'),
                headers=('ID', 'Название', 'Категория', 'Тип', 'Ед.'),
            )
        elif args.full:
            print_list_verbose(items)
        else:
            print_list_items(items)


def cmd_get(args: argparse.Namespace) -> None:
    with session_scope() as db:
        obj = product_crud.get_or_raise(db=db, obj_id=args.id)
        print_item(obj)


def cmd_update(args: argparse.Namespace) -> None:
    with session_scope() as db:
        obj = product_crud.update(
            db=db,
            obj_id=args.id,
            commit=True,
            name=args.name,
            category_id=args.category_id,
            unit_id=args.unit_id,
        )
        print_item(obj)


def cmd_delete(args: argparse.Namespace) -> None:
    with session_scope() as db:
        product_crud.delete(db=db, obj_id=args.id, commit=True)
        print(f'OK deleted id={args.id}')
