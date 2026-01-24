"""CLI-команды для покупок."""

from __future__ import annotations

import argparse

from app.cli.common import parse_date
from app.cli.crud_commands import (
    ArgSpec,
    CrudCommandSpec,
    TableSpec,
    register_crud_commands,
)
from app.core.constants import ORDER_MAP
from app.crud.purchases import crud as purchase_crud
from app.models import Purchase
from app.service.purchases import (
    create_purchase,
    delete_purchase,
    get_purchase_by_id,
    get_purchase_by_product,
    get_purchase_by_store,
    list_purchases,
    update_purchase,
)


def _create(
    args: argparse.Namespace
) -> Purchase:
    return create_purchase(
        store_id=args.store_id,
        product_id=args.product_id,
        quantity=args.quantity,
        price=args.total_price,
        purchase_date=args.date,
        comment=args.comment,
        is_promo=args.promo,
        promo_type=args.promo_type,
        regular_unit_price=args.regular_unit_price,
    )


def _update(args: argparse.Namespace) -> Purchase:
    if args.promo and args.no_promo:
        raise ValueError('Нельзя одновременно --promo и --no-promo')

    if args.no_promo and (
        args.promo_type is not None or args.regular_unit_price is not None
    ):
        raise ValueError(
            'С --no-promo нельзя передавать --promo-type/--regular-unit-price'
        )

    is_promo = None
    if args.promo:
        is_promo = True
    elif args.no_promo:
        is_promo = False

    return update_purchase(
        purchase_id=args.id,
        store_id=args.store_id,
        product_id=args.product_id,
        total_price=args.total_price,
        quantity=args.quantity,
        comment=args.comment,
        purchase_date=args.date,
        is_promo=is_promo,
        promo_type=args.promo_type,
        regular_unit_price=args.regular_unit_price,
    )


def _list(args: argparse.Namespace) -> list[Purchase]:
    promo_filter = None
    if args.promo_only and args.no_promo_only:
        raise ValueError('Нельзя одновременно --promo-only и --no-promo-only')
    if args.promo_only:
        promo_filter = True
    if args.no_promo_only:
        promo_filter = False

    if args.product_id is not None:
        return get_purchase_by_product(
            product_id=args.product_id,
            from_date=args.from_date,
            to_date=args.to_date,
            is_promo=promo_filter,
        )

    if args.store_id is not None:
        items = get_purchase_by_store(
            store_id=args.store_id,
            is_promo=promo_filter
        )
        if args.from_date is not None:
            items = [
                item for item in items if item.purchase_date >= args.from_date
            ]
        if args.to_date is not None:
            items = [
                item for item in items if item.purchase_date <= args.to_date
            ]
        return items

    order_col = ORDER_MAP[args.order]
    return list_purchases(
        offset=args.offset,
        limit=args.limit,
        order_by=order_col,
        is_promo=promo_filter,
    )


def register_purchase_commands(
    subparsers: argparse._SubParsersAction
) -> None:
    spec = CrudCommandSpec(
        command='purchase',
        help='Управление покупками.',
        crud=purchase_crud,
        model_cls=Purchase,

        # add
        add_args=[
            ArgSpec(
                ('--date',),
                {
                    'type': parse_date, 'default': None,
                    'help': 'Дата покупки (YYYY-MM-DD). default сегодня.'
                }
            ),
            ArgSpec(
                ('-p', '--product-id'),
                {
                    'type': int,
                    'required': True,
                    'help': 'Продукт (ID).'
                }
            ),
            ArgSpec(('-s', '--store-id'),
                    {
                        'type': int,
                        'required': True,
                        'help': 'Магазин (ID).'
                    }
                ),
            ArgSpec(
                ('-q', '--quantity'),
                {
                    'type': float,
                    'required': True, 'help':
                    'Количество (упаковок).'
                }
            ),
            ArgSpec(
                ('-tp', '--total-price'),
                {
                    'type': float,
                    'required': True,
                    'help': 'Сумма по чеку.'
                }
            ),
            ArgSpec(
                ('-c', '--comment'),
                {
                    'default': None,
                    'help': 'Комментарий.'
                }
            ),
            ArgSpec(
                ('--promo',),
                {
                    'action': 'store_true',
                    'help': 'Покупка по акции'
                }
            ),
            ArgSpec(
                ('--promo-type',),
                {
                    'default': None,
                    'help': 'Тип акции (discount/multi_buy/...)'
                }
            ),
            ArgSpec(
                ('--regular-unit-price',),
                {
                    'type': float,
                    'default': None,
                    'help': 'Обычная цена за единицу (если знаешь)'
                }
            ),
        ],

        # update
        update_args=[
            ArgSpec(
                ('--date',),
                {
                    'type': parse_date,
                    'default': None,
                    'help': 'Новая дата (YYYY-MM-DD).'
                }
            ),
            ArgSpec(
                ('--product-id',),
                {'type': int, 'default': None}
            ),
            ArgSpec(
                ('--store-id',),
                {'type': int, 'default': None}
            ),
            ArgSpec(
                ('--quantity',),
                {'type': float, 'default': None}
            ),
            ArgSpec(
                ('--total-price',),
                {'type': float, 'default': None}
            ),
            ArgSpec(
                ('--comment',),
                {'default': None}
            ),
            ArgSpec(
                ('--promo',),
                {
                    'action': 'store_true',
                    'help': 'Сделать покупку акционной'
                }
            ),
            ArgSpec(
                ('--no-promo',),
                {
                    'action': 'store_true',
                    'help': 'Снять флаг акции и очистить поля промо'
                }
            ),
            ArgSpec(
                ('--promo-type',),
                {
                    'default': None,
                    'help': 'Тип акции'
                }
            ),
            ArgSpec(
                ('--regular-unit-price',),
                {
                    'type': float,
                    'default': None,
                    'help': 'Обычная цена за единицу'
                }
            ),
        ],

        create_fields=(),
        update_fields=(),

        order_by=ORDER_MAP,
        default_order='purchase_date',

        list_args=[
            ArgSpec(
                ('--product-id',),
                {
                    'type': int,
                    'default': None,
                    'help': 'Фильтр по продукту (ID)'
                }
            ),
            ArgSpec(
                ('--store-id',),
                {
                    'type': int,
                    'default': None,
                    'help': 'Фильтр по магазину (ID)'
                }
            ),
            ArgSpec(
                ('--from-date',),
                {
                    'type': parse_date,
                    'default': None,
                    'help': 'Дата начала (YYYY-MM-DD)'
                }
            ),
            ArgSpec(
                ('--to-date',),
                {
                    'type': parse_date,
                    'default': None,
                    'help': 'Дата конца (YYYY-MM-DD)'
                }
            ),
            ArgSpec(
                ('--promo-only',),
                {
                    'action': 'store_true',
                    'help': 'Показать только акционные'
                }
            ),
            ArgSpec(
                ('--no-promo-only',),
                {
                    'action': 'store_true',
                    'help': 'Показать только неакционные'
                }
            ),
        ],

        table=TableSpec(
            columns=(
                'id', 'purchase_date', 'product', 'category',
                'quantity', 'unit', 'total_price', 'unit_price',
                'is_promo', 'promo_type', 'regular_unit_price',
                'store',
            ),
            headers=(
                'ID', 'Дата', 'Товар', 'Категория',
                'Кол-во', 'Ед.', 'Сумма', 'Цена/ед',
                'Акция', 'Тип акции', 'Обычн./ед',
                'Магазин',
            ),
        ),

        create_fn=_create,
        update_fn=_update,
        delete_fn=lambda obj_id: delete_purchase(purchase_id=obj_id),
        get_fn=lambda obj_id: get_purchase_by_id(purchase_id=obj_id),
        list_fn=_list,
    )

    register_crud_commands(subparsers, spec)
