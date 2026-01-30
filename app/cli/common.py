"""Общие утилиты CLI."""

from __future__ import annotations

import argparse
import os
from collections.abc import Sequence
from datetime import date
from typing import Any, Optional

from prettytable import PrettyTable

from app.core.constants import (
    CLI_DEFAULT_LIMIT,
    CLI_DEFAULT_OFFSET,
    CLI_VERBOSE_SEPARATOR_LEN,
    DB_URL_ENV_VAR,
    DEFAULT_DB_URL,
)
from app.core.db import init_db
from app.core.migrations import ensure_db_schema


def configure_db(
    db_url: Optional[str],
    echo_sql: bool = False,
) -> None:
    """Настроить подключение к базе данных для CLI.

    Args:
        db_url: URL базы данных
        (если None — выбирается через settings.get_db_url()).
        echo_sql: Включить вывод SQL-запросов.

    Returns:
        None
    """
    url = db_url or os.getenv(DB_URL_ENV_VAR, DEFAULT_DB_URL)
    init_db(db_url=url, echo=echo_sql)

    is_memory = ':memory:' in url
    if not is_memory:
        ensure_db_schema(url)


def parse_date(value: str) -> date:
    """Преобразовать строку даты из CLI в `datetime.date`.

    Args:
        value: Дата в формате `YYYY-MM-DD`.

    Returns:
        date: Преобразованная дата.

    Raises:
        ValueError: Если строка не соответствует формату `YYYY-MM-DD`.
    """
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
    """Вывести список объектов в виде таблицы (PrettyTable)."""
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
    """Вывести один объект в “человеческом” формате."""
    data = obj.to_dict() if hasattr(obj, 'to_dict') else obj
    if isinstance(data, dict):
        for k, v in data.items():
            print(f'{k}: {v}')
    else:
        print(data)


def print_list_items(objs: list[Any]) -> None:
    """Вывести список объектов в компактном режиме."""
    for obj in objs:
        data = obj.to_dict()
        if 'id' in data and 'name' in data:
            print('-' * CLI_VERBOSE_SEPARATOR_LEN)
        else:
            print(data)


def print_list_verbose(objs: list[Any]) -> None:
    """Вывести список объектов в подробном режиме."""
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
    """Добавить стандартные аргументы для команды `list`."""
    parser.add_argument(
        '-o',
        '--offset',
        type=int,
        default=CLI_DEFAULT_OFFSET,
        help='Смещение для пагинации',
    )
    parser.add_argument(
        '-l',
        '--limit',
        type=int,
        default=CLI_DEFAULT_LIMIT,
        help='Лимит для пагинации',
    )
    parser.add_argument(
        '--order',
        choices=order_choices,
        default=default_order,
        help='Поле сортировки',
    )
