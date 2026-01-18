from __future__ import annotations

import argparse

from app.cli.common import print_item, print_list_items, session_scope
from app.crud.stores import crud as store_crud
from app.models import Store


def register_store_commands(
    subparsers: argparse._SubParsersAction,
) -> None:
    pars = subparsers.add_parser(
        'store',
        help='Управление категориями покупок.',
    )
    subpars = pars.add_subparsers(
        dest='action',
        required=True,
    )

    add = subpars.add_parser(
        'add',
        help='Добавить магазин.',
    )
    add.add_argument('name', help='Название магазина.')
    add.add_argument(
        '-d',
        '--description',
        default=None,
        help='Описание магазина.',
    )
    add.set_defaults(func=cmd_add)

    lst = subpars.add_parser('list', help='Список магазинов')
    lst.add_argument(
        '-o',
        '--offset',
        type=int,
        default=0,
        help='Смещение для пагинации (по умолчанию 0).',
    )
    lst.add_argument(
        '-l',
        '--limit',
        type=int,
        default=100,
        help='Лимит для пагинации (по умолчанию 100).',
    )
    lst.add_argument(
        '--order',
        choices=('id', 'name'),
        default='id',
        help='Поле сортировки.',
    )
    lst.set_defaults(func=cmd_list)

    get = subpars.add_parser('get', help='Получить магазин по id')
    get.add_argument('id', type=int)
    get.set_defaults(func=cmd_get)

    upd = subpars.add_parser('update', help='Обновить магазин')
    upd.add_argument('id', type=int)
    upd.add_argument('--name', default=None)
    upd.add_argument('--description', default=None)
    upd.set_defaults(func=cmd_update)

    rm = subpars.add_parser('delete', help='Удалить магазин')
    rm.add_argument('id', type=int)
    rm.set_defaults(func=cmd_delete)


def cmd_add(args: argparse.Namespace) -> None:
    with session_scope() as db:
        obj = Store(name=args.name, description=args.description)
        obj = store_crud.create(db=db, obj_in=obj, commit=True)
        print_item(obj)


def cmd_list(args: argparse.Namespace) -> None:
    with session_scope() as db:
        order_col = Store.id if args.order == 'id' else Store.name
        items = store_crud.list(
            db=db,
            offset=args.offset,
            limit=args.limit,
            order_by=order_col,
        )
        print_list_items(items)


def cmd_get(args: argparse.Namespace) -> None:
    with session_scope() as db:
        obj = store_crud.get_or_raise(db=db, obj_id=args.id)
        print_item(obj)


def cmd_update(args: argparse.Namespace) -> None:
    with session_scope() as db:
        obj = store_crud.update(
            db=db,
            obj_id=args.id,
            commit=True,
            name=args.name,
            description=args.description,
        )
        print_item(obj)


def cmd_delete(args: argparse.Namespace) -> None:
    with session_scope() as db:
        store_crud.delete(db=db, obj_id=args.id, commit=True)
        print(f'OK deleted id={args.id}')
