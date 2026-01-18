from __future__ import annotations

import argparse

from app.cli.common import (
    add_list_args,
    print_item,
    print_list_items,
    print_list_verbose,
    session_scope,
    print_table
)
from app.crud.units import crud as unit_crud
from app.models import Unit


def register_unit_commands(subparsers: argparse._SubParsersAction) -> None:
    pars = subparsers.add_parser(
        'units',
        help='Управление единицами измерения (Е.И.) покупок.',
    )
    subpars = pars.add_subparsers(dest='action', required=True)

    add = subpars.add_parser('add', help='Добавить единицу измерений.')
    add.add_argument('unit', help='Единица измерения (кг, л, шт и т.д.).')
    add.add_argument(
        '-mt',
        '--measure-type',
        required=True,
        help='Тип единицы измерения (Вес, Объем и т.д.).',
    )
    add.set_defaults(func=cmd_add)

    lst = subpars.add_parser('list', help='Список единиц измерений')
    grp = lst.add_mutually_exclusive_group()
    grp.add_argument(
        '--full',
        action='store_true',
        help='key: value для каждого объекта'
    )
    grp.add_argument(
        '--table',
        action='store_true',
        help='табличный вывод'
    )
    add_list_args(
        lst,
        order_choices=('id', 'unit'),
        default_order='id',
    )
    lst.set_defaults(func=cmd_list)

    get = subpars.add_parser('get', help='Получить ед. изм. по id')
    get.add_argument('id', type=int)
    get.set_defaults(func=cmd_get)

    upd = subpars.add_parser('update', help='Обновить ед. изм.')
    upd.add_argument('id', type=int)
    upd.add_argument('--unit', default=None)
    upd.add_argument('--measure-type', default=None)
    upd.set_defaults(func=cmd_update)

    rm = subpars.add_parser('delete', help='Удалить ед. изм.')
    rm.add_argument('id', type=int)
    rm.set_defaults(func=cmd_delete)


def cmd_add(args: argparse.Namespace) -> None:
    with session_scope() as db:
        obj = Unit(unit=args.unit, measure_type=args.measure_type)
        obj = unit_crud.create(db=db, obj_in=obj, commit=True)
        print_item(obj)


def cmd_list(args: argparse.Namespace) -> None:
    with session_scope() as db:
        order_col = Unit.id if args.order == 'id' else Unit.unit
        items = unit_crud.list(db=db, offset=args.offset,
                               limit=args.limit, order_by=order_col)
        if args.table:
            print_table(
                items,
                columns=('id', 'measure_type', 'unit'),
                headers=('ID', 'Тип', 'Ед.'),
            )
        elif args.full:
            print_list_verbose(items)
        else:
            print_list_items(items)


def cmd_get(args: argparse.Namespace) -> None:
    with session_scope() as db:
        obj = unit_crud.get_or_raise(db=db, obj_id=args.id)
        print_item(obj)


def cmd_update(args: argparse.Namespace) -> None:
    with session_scope() as db:
        obj = unit_crud.update(
            db=db,
            obj_id=args.id,
            commit=True,
            unit=args.unit,
            measure_type=args.measure_type,
        )
        print_item(obj)


def cmd_delete(args: argparse.Namespace) -> None:
    with session_scope() as db:
        unit_crud.delete(db=db, obj_id=args.id, commit=True)
        print(f'OK deleted id={args.id}')
