from __future__ import annotations

import argparse
from datetime import date

from app.models import Purchase
from app.crud.purchases import crud as purchase_crud
from app.service.purchases import create_purchase, update_purchase
from app.cli.common import print_item, print_list_items, session_scope


ORDER_MAP = {
    'id': Purchase.id,
    'product': Purchase.product_id,
    'purchase_date': Purchase.purchase_date,
    'store': Purchase.store_id,
    'quantity': Purchase.quantity,
}


def add_purchase_fields(parser: argparse.ArgumentParser) -> None:
    """Общие поля для add/update."""
    parser.add_argument('-p', '--product-id', type=int,
                        required=True, help='Продукт (ID).')
    parser.add_argument('-s', '--store-id', type=int,
                        default=None, help='Магазин (ID).')
    parser.add_argument('-q', '--quantity', type=float,
                        default=None, help='Количество товара (упаковок).')
    parser.add_argument('-tp', '--total-price', type=float,
                        default=None, help='Общая стоимость (по чеку).')
    parser.add_argument('-c', '--comment', default=None,
                        help='Комментарий к покупке.')


def register_purchase_commands(
    subparsers: argparse._SubParsersAction
) -> None:
    pars = subparsers.add_parser(
        'purchase',
        help='Управление покупками.',
    )
    subpars = pars.add_subparsers(
        dest='action',
        required=True,
    )

    add = subpars.add_parser(
        'add',
        help='Добавить покупку.',
    )
    add.add_argument(
        '--date',
        type=date.fromisoformat,
        default=date.today(),
        help='Дата покупки (YYYY-MM-DD)',
    )
    add_purchase_fields(add)
    add.set_defaults(func=cmd_add)

    lst = subpars.add_parser('list', help='Список товаров')
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
        choices=('id', 'product', 'purchase_date', 'store', 'quantity'),
        default='id',
        help='Поле сортировки.',
    )
    lst.set_defaults(func=cmd_list)

    get = subpars.add_parser('get', help='Получить покупку по id')
    get.add_argument('id', type=int)
    get.set_defaults(func=cmd_get)

    upd = subpars.add_parser('update', help='Обновить покупку')
    upd.add_argument('id', type=int)
    add_purchase_fields(upd)
    upd.set_defaults(func=cmd_update)

    rm = subpars.add_parser('delete', help='Удалить покупку')
    rm.add_argument('id', type=int)
    rm.set_defaults(func=cmd_delete)


def cmd_add(args: argparse.Namespace) -> None:
    with session_scope() as db:
        obj = create_purchase(
            product_id=args.product_id,
            store_id=args.store_id,
            quantity=args.quantity,
            price=args.total_price,
            purchase_date=args.date,
            comment=args.comment,
        )
        obj = purchase_crud.get_with_normal_attr_or_raise(db=db, obj_id=obj.id)
        print_item(obj)


def cmd_list(args: argparse.Namespace) -> None:
    with session_scope() as db:
        order_col = ORDER_MAP[args.order]
        items = purchase_crud.list(
            db=db,
            offset=args.offset,
            limit=args.limit,
            order_by=order_col,
        )
        print_list_items(items)


def cmd_get(args: argparse.Namespace) -> None:
    with session_scope() as db:
        obj = purchase_crud.get_with_normal_attr_or_raise(
            db=db,
            obj_id=args.id
        )
        print_item(obj)


def cmd_update(args: argparse.Namespace) -> None:
    with session_scope() as db:
        obj = update_purchase(
            db=db,
            obj_id=args.id,
            product_id=args.product_id,
            store_id=args.store_id,
            quantity=args.quantity,
            total_price=args.total_price,
            comment=args.comment,
            commit=True,
        )
        obj = purchase_crud.get_with_normal_attr_or_raise(
            db=db,
            obj_id=obj.id,
        )
        print_item(obj)


def cmd_delete(args: argparse.Namespace) -> None:
    with session_scope() as db:
        purchase_crud.delete(db=db, obj_id=args.id, commit=True)
        print(f'OK deleted id={args.id}')
