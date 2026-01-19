from __future__ import annotations

import argparse

from app.cli.common import (
    add_list_args,
    print_item,
    print_list_items,
    print_list_verbose,
    print_table,
)
from app.crud import product_crud
from app.models import Product
from app.service.crud_service import (
    create_item,
    delete_item,
    list_items,
    update_item,
)
from app.service.product import get_product


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
    obj = Product(
        name=args.name,
        category_id=args.category_id,
        unit_id=args.unit_id,
    )
    obj = get_product(product_id=args.id)
    print_item(obj)


def cmd_list(args: argparse.Namespace) -> None:
    order_col = Product.id if args.order == 'id' else Product.name
    items = list_items(
        crud=product_crud,
        offset=args.offset,
        limit=args.limit,
        order_by=order_col,
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
    obj = get_product(product_id=args.id)
    print_item(obj)


def cmd_update(args: argparse.Namespace) -> None:
    obj = update_item(
        crud=product_crud,
        item_id=args.id,
        name=args.name,
        category_id=args.category_id,
        unit_id=args.unit_id,
    )
    obj = get_product(product_id=args.id)
    print_item(obj)


def cmd_delete(args: argparse.Namespace) -> None:
    delete_item(crud=product_crud, item_id=args.id)
    print(f'OK deleted id={args.id}')
