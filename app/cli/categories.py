from __future__ import annotations

import argparse

from app.cli.common import (
    add_list_args,
    print_item,
    print_list_items,
    print_list_verbose,
    print_table,
)
from app.crud import category_crud
from app.models import Category
from app.service.crud_service import (
    create_item,
    delete_item,
    get_item,
    list_items,
    update_item,
)


def register_category_commands(
    subparsers: argparse._SubParsersAction,
) -> None:
    pars = subparsers.add_parser(
        'category',
        help='Управление категориями покупок.',
    )
    subpars = pars.add_subparsers(
        dest='action',
        required=True,
    )

    add = subpars.add_parser(
        'add',
        help='Добавить категорию.',
    )
    add.add_argument('name', help='Название категории.')
    add.add_argument(
        '-d',
        '--description',
        default=None,
        help='Описание категории.',
    )
    add.set_defaults(func=cmd_add)

    lst = subpars.add_parser('list', help='Список категорий')
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

    get = subpars.add_parser('get', help='Получить категорию по id')
    get.add_argument('id', type=int)
    get.set_defaults(func=cmd_get)

    upd = subpars.add_parser('update', help='Обновить категорию')
    upd.add_argument('id', type=int)
    upd.add_argument('--name', default=None)
    upd.add_argument('--description', default=None)
    upd.set_defaults(func=cmd_update)

    rm = subpars.add_parser('delete', help='Удалить категорию')
    rm.add_argument('id', type=int)
    rm.set_defaults(func=cmd_delete)


def cmd_add(args: argparse.Namespace) -> None:
    obj = Category(name=args.name, description=args.description)
    obj = create_item(crud=category_crud, obj_in=obj)
    print_item(obj)


def cmd_list(args: argparse.Namespace) -> None:
    order_col = Category.id if args.order == 'id' else Category.name
    items = list_items(
        crud=category_crud,
        offset=args.offset,
        limit=args.limit,
        order_by=order_col,
    )
    if args.table:
        print_table(
            items,
            columns=('id', 'name', 'description'),
            headers=('ID', 'Название', 'Описание'),
        )
    elif args.full:
        print_list_verbose(items)
    else:
        print_list_items(items)


def cmd_get(args: argparse.Namespace) -> None:
    obj = get_item(crud=category_crud, item_id=args.id)
    print_item(obj)


def cmd_update(args: argparse.Namespace) -> None:
    obj = update_item(
        crud=category_crud,
        item_id=args.id,
        name=args.name,
        description=args.description,
    )
    print_item(obj)


def cmd_delete(args: argparse.Namespace) -> None:
    delete_item(crud=category_crud, item_id=args.id)
    print(f'OK deleted id={args.id}')
