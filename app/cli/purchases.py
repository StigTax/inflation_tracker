from __future__ import annotations

import argparse

from app.cli.common import parse_date, print_item, print_list_items, session_scope
from app.crud.purchases import crud as purchase_crud
from app.models import Purchase
from app.service.purchases import create_purchase, update_purchase


ORDER_MAP = {
    'id': Purchase.id,
    'product': Purchase.product_id,
    'purchase_date': Purchase.purchase_date,
    'store': Purchase.store_id,
    'quantity': Purchase.quantity,
}


def add_purchase_fields(parser: argparse.ArgumentParser, *, required: bool) -> None:
    """Поля для add/update.

    Для add: required=True, для update: required=False.
    """
    parser.add_argument(
        '-p',
        '--product-id',
        type=int,
        required=required,
        help='Продукт (ID).',
    )
    parser.add_argument(
        '-s',
        '--store-id',
        type=int,
        required=required,
        default=None,
        help='Магазин (ID).',
    )
    parser.add_argument(
        '-q',
        '--quantity',
        type=float,
        required=required,
        default=None,
        help='Количество товара (упаковок).',
    )
    parser.add_argument(
        '-tp',
        '--total-price',
        type=float,
        required=required,
        default=None,
        help='Общая стоимость (по чеку).',
    )
    parser.add_argument(
        '-c',
        '--comment',
        default=None,
        help='Комментарий к покупке.',
    )


def register_purchase_commands(subparsers: argparse._SubParsersAction) -> None:
    pars = subparsers.add_parser(
        'purchase',
        help='Управление покупками.',
    )
    subpars = pars.add_subparsers(dest='action', required=True)

    add = subpars.add_parser('add', help='Добавить покупку.')
    add.add_argument(
        '--date',
        type=parse_date,
        default=None,
        help='Дата покупки (YYYY-MM-DD). Если не указана — сегодня.',
    )
    add_purchase_fields(add, required=True)
    add.set_defaults(func=cmd_add)

    lst = subpars.add_parser('list', help='Список покупок')
    lst.add_argument('-o', '--offset', type=int, default=0,
                     help='Смещение для пагинации (по умолчанию 0).')
    lst.add_argument('-l', '--limit', type=int, default=100,
                     help='Лимит для пагинации (по умолчанию 100).')
    lst.add_argument('--order',
                     choices=('id', 'product', 'purchase_date',
                              'store', 'quantity'),
                     default='id',
                     help='Поле сортировки.')
    lst.set_defaults(func=cmd_list)

    get = subpars.add_parser('get', help='Получить покупку по id')
    get.add_argument('id', type=int)
    get.set_defaults(func=cmd_get)

    upd = subpars.add_parser('update', help='Обновить покупку')
    upd.add_argument('id', type=int)
    upd.add_argument(
        '--date',
        type=parse_date,
        default=None,
        help='Новая дата покупки (YYYY-MM-DD).',
    )
    add_purchase_fields(upd, required=False)
    upd.set_defaults(func=cmd_update)

    rm = subpars.add_parser('delete', help='Удалить покупку')
    rm.add_argument('id', type=int)
    rm.set_defaults(func=cmd_delete)


def cmd_add(args: argparse.Namespace) -> None:
    obj = create_purchase(
        store_id=args.store_id,
        product_id=args.product_id,
        quantity=args.quantity,
        price=args.total_price,
        purchase_date=args.date,
        comment=args.comment,
    )
    with session_scope() as db:
        obj = purchase_crud.get_with_normal_attr_or_raise(db=db, obj_id=obj.id)
        print_item(obj)


def cmd_list(args: argparse.Namespace) -> None:
    with session_scope() as db:
        order_col = ORDER_MAP[args.order]
        items = purchase_crud.list(
            db=db, offset=args.offset, limit=args.limit, order_by=order_col)
        print_list_items(items)


def cmd_get(args: argparse.Namespace) -> None:
    with session_scope() as db:
        obj = purchase_crud.get_with_normal_attr_or_raise(
            db=db, obj_id=args.id)
        print_item(obj)


def cmd_update(args: argparse.Namespace) -> None:
    obj = update_purchase(
        purchase_id=args.id,
        store_id=args.store_id,
        product_id=args.product_id,
        quantity=args.quantity,
        total_price=args.total_price,
        comment=args.comment,
        purchase_date=args.date,
    )
    with session_scope() as db:
        obj = purchase_crud.get_with_normal_attr_or_raise(db=db, obj_id=obj.id)
        print_item(obj)


def cmd_delete(args: argparse.Namespace) -> None:
    with session_scope() as db:
        purchase_crud.delete(db=db, obj_id=args.id, commit=True)
        print(f'OK deleted id={args.id}')
