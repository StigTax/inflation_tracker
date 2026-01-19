from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional, Sequence, TypeVar

from app.cli.common import (
    add_list_args,
    print_item,
    print_list_verbose,
    print_table,
)
from app.service.crud_service import (
    create_item,
    delete_item,
    get_item,
    list_items,
    update_item,
)

ModelT = TypeVar("ModelT")


@dataclass(frozen=True)
class ArgSpec:
    args: tuple[str, ...]
    kwargs: Mapping[str, Any]


@dataclass(frozen=True)
class TableSpec:
    columns: tuple[str, ...]
    headers: tuple[str, ...]


@dataclass(frozen=True)
class CrudCommandSpec:
    command: str
    help: str

    crud: Any
    model_cls: type

    add_args: Sequence[ArgSpec]
    update_args: Sequence[ArgSpec]

    create_fields: tuple[str, ...]
    update_fields: tuple[str, ...]

    order_by: Mapping[str, Any]
    default_order: str

    table: TableSpec

    list_args: Sequence[ArgSpec] = ()

    create_fn: Optional[Callable[[argparse.Namespace], Any]] = None
    update_fn: Optional[Callable[[argparse.Namespace], Any]] = None
    delete_fn: Optional[Callable[[int], None]] = None
    list_fn: Optional[Callable[[argparse.Namespace], Sequence[Any]]] = None

    get_fn: Optional[Callable[[int], Any]] = None
    refresh_after_write: bool = False


def register_crud_commands(
    subparsers: argparse._SubParsersAction,
    spec: CrudCommandSpec,
) -> None:
    pars = subparsers.add_parser(
        spec.command, help=spec.help,
    )
    subpars = pars.add_subparsers(dest='action', required=True)

    add = subpars.add_parser(
        'add',
        help=f'Добавить {spec.command}.',
    )
    for add_arg in spec.add_args:
        add.add_argument(
            *add_arg.args,
            **dict(add_arg.kwargs)
        )
    add.set_defaults(
        func=_make_cmd_add(spec)
    )

    lst = subpars.add_parser(
        'list',
        help=f'Список {spec.command}',
    )
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
        order_choices=tuple(spec.order_by.keys()),
        default_order=spec.default_order
    )
    for a in spec.list_args:
        lst.add_argument(*a.args, **dict(a.kwargs))
    lst.set_defaults(func=_make_cmd_list(spec))

    getp = subpars.add_parser(
        'get',
        help=f'Получить {spec.command} по ID'
    )
    getp.add_argument(
        'id',
        type=int
    )
    getp.set_defaults(func=_make_cmd_get(spec))

    upd = subpars.add_parser(
        'update',
        help=f'Обновить {spec.command}'
    )
    upd.add_argument(
        'id',
        type=int
    )
    for upd_arg in spec.update_args:
        upd.add_argument(*upd_arg.args, **dict(upd_arg.kwargs))
    upd.set_defaults(func=_make_cmd_update(spec))

    rm = subpars.add_parser("delete", help=f"Удалить {spec.command}")
    rm.add_argument("id", type=int)
    rm.set_defaults(func=_make_cmd_delete(spec))


def _make_cmd_add(
    spec: CrudCommandSpec
):
    def cmd(
        args: argparse.Namespace
    ) -> None:
        if spec.create_fn is not None:
            created = spec.create_fn(args)
        else:
            payload = {
                key: getattr(args, key) for key in spec.create_fields
            }
            obj_in = spec.model_cls(**payload)

            created = create_item(crud=spec.crud, obj_in=obj_in)

        if spec.refresh_after_write:
            getter = spec.get_fn or (
                lambda obj_id: get_item(crud=spec.crud, item_id=obj_id)
            )
            created = getter(created.id)

        print_item(created)

    return cmd


def _make_cmd_list(spec: CrudCommandSpec):
    def cmd(args: argparse.Namespace) -> None:
        if spec.list_fn is not None:
            items = spec.list_fn(args)
        else:
            order_col = spec.order_by[args.order]
            items = list_items(
                crud=spec.crud,
                offset=args.offset,
                limit=args.limit,
                order_by=order_col,
            )

        if args.full:
            print_list_verbose(items)
        else:
            # default -> table
            print_table(
                items,
                columns=spec.table.columns,
                headers=spec.table.headers
            )

    return cmd


def _make_cmd_get(spec: CrudCommandSpec):
    def cmd(args: argparse.Namespace) -> None:
        getter = spec.get_fn or (
            lambda obj_id: get_item(crud=spec.crud, item_id=obj_id)
        )
        obj = getter(args.id)
        print_item(obj)

    return cmd


def _make_cmd_update(spec: CrudCommandSpec):
    def cmd(args: argparse.Namespace) -> None:
        if spec.update_fn is not None:
            updated = spec.update_fn(args)
        else:
            fields: dict[str, Any] = {}
            for k in spec.update_fields:
                v = getattr(args, k)
                if v is not None:
                    fields[k] = v

            updated = update_item(
                crud=spec.crud,
                item_id=args.id,
                **fields
            )

        if spec.refresh_after_write:
            getter = spec.get_fn or (
                lambda obj_id: get_item(crud=spec.crud, item_id=obj_id)
            )
            updated = getter(updated.id)

        print_item(updated)

    return cmd


def _make_cmd_delete(spec: CrudCommandSpec):
    def cmd(args: argparse.Namespace) -> None:
        if spec.delete_fn is not None:
            spec.delete_fn(args.id)
        else:
            delete_item(crud=spec.crud, item_id=args.id)
        print(f"OK deleted id={args.id}")

    return cmd
