from __future__ import annotations

import argparse
import os
from collections.abc import Sequence
from datetime import date
from typing import Any, Optional

from prettytable import PrettyTable

from app.core.db import init_db


def configure_db(
    db_url: Optional[str] = None,
    echo_sql: bool = False,
) -> None:
    url = db_url or os.getenv(
        'DB_URL',
        'sqlite+pysqlite:///./inflation.db',
    )
    init_db(url, echo=echo_sql)


def parse_date(value: str) -> date:
    try:
        value = date.fromisoformat(value)
    except ValueError:
        raise ValueError(
            f'Неверный формат даты: {value}. '
            'Ожидается формат ГГГГ-ММ-ДД.',
        )
    return value


def print_table(
    objs: Sequence[Any],
    columns: Optional[Sequence[str]] = None,
    headers: Optional[Sequence[str]] = None,
) -> None:
    if not objs:
        print('(пусто)')
        return

    first = objs[0].to_dict()
    if columns is None:
        columns = list(first.keys())

    if headers is None:
        headers = list(columns)

    t = PrettyTable(headers)
    t.align = 'l'

    for obj in objs:
        data = obj.to_dict()
        row = [data.get(col) for col in columns]
        t.add_row(row)

    print(t)


def print_item(obj: Any) -> None:
    data = obj.to_dict() if hasattr(obj, "to_dict") else obj
    if isinstance(data, dict):
        for k, v in data.items():
            print(f"{k}: {v}")
    else:
        print(data)


def print_list_items(objs: list[Any]) -> None:
    for obj in objs:
        data = obj.to_dict()
        if 'id' in data and 'name' in data:
            print(f'{data["id"]}\t{data["name"]}')
        else:
            print(data)


def print_list_verbose(objs: list[Any]) -> None:
    for idx, obj in enumerate(objs):
        if idx:
            print('-' * 40)
        print_item(obj)


def add_list_args(
    parser: argparse.ArgumentParser,
    *,
    order_choices: tuple[str, ...],
    default_order: str = 'id',
) -> None:
    parser.add_argument(
        '-o',
        '--offset',
        type=int,
        default=0,
        help='Смещение для пагинации',
    )
    parser.add_argument(
        '-l',
        '--limit',
        type=int,
        default=100,
        help='Лимит для пагинации',
    )
    parser.add_argument(
        '--order',
        choices=order_choices,
        default=default_order,
        help='Поле сортировки',
    )
