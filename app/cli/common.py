"""Общие утилиты CLI."""

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
    """Настроить подключение к базе данных для CLI.

    Функция выбирает URL БД в таком порядке:
    1) аргумент `db_url`,
    2) переменная окружения `DB_URL`,
    3) дефолтный SQLite-файл `./inflation.db`.

    После выбора URL вызывает `init_db(...)` и включает вывод SQL при
    `echo_sql=True`.

    Args:
        db_url: URL базы данных
          (например, `sqlite+pysqlite:///./inflation.db`).
        echo_sql: Включить вывод SQL-запросов в консоль.

    Returns:
        None
    """
    url = db_url or os.getenv(
        'DB_URL',
        'sqlite+pysqlite:///./inflation.db',
    )
    init_db(url, echo=echo_sql)


def parse_date(value: str) -> date:
    """Преобразовать строку даты из CLI в `datetime.date`.

    Принимает дату в ISO-формате `YYYY-MM-DD` и возвращает объект `date`.

    Args:
        value: Дата в формате `YYYY-MM-DD`.

    Returns:
        date: Дата, преобразованная в тип `datetime.date`.

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
    """Вывести список объектов в виде таблицы (PrettyTable).

    Ожидается, что элементы `objs` поддерживают метод `to_dict()`.
    Если `columns` не задан — берутся ключи из `to_dict()` первого объекта.
    Если список пуст — печатается `(пусто)`.

    Args:
        objs: Последовательность объектов для вывода (обычно модели/DTO с
          `to_dict()`).
        columns: Порядок колонок (ключи словаря `to_dict()`).
        headers: Заголовки колонок в том же порядке, что `columns`.

    Returns:
        None
    """
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
    """Вывести один объект в “человеческом” формате.

    Если объект имеет `to_dict()`, выводится словарь.
    Если результат — `dict`, печатается построчно `key: value`.
    Иначе печатается как есть.

    Args:
        obj: Объект для вывода (модель/DTO/словарь/строка и т.д.).

    Returns:
        None
    """
    data = obj.to_dict() if hasattr(obj, 'to_dict') else obj
    if isinstance(data, dict):
        for k, v in data.items():
            print(f'{k}: {v}')
    else:
        print(data)


def print_list_items(objs: list[Any]) -> None:
    """Вывести список объектов в компактном режиме.

    Для объектов с `to_dict()` и ключами `id` и `name` печатает строку:
    `id<TAB>name`. В остальных случаях печатает словарь целиком.

    Args:
        objs: Список объектов (ожидается `to_dict()`).

    Returns:
        None
    """
    for obj in objs:
        data = obj.to_dict()
        if 'id' in data and 'name' in data:
            print(f'{data["id"]}\t{data["name"]}')
        else:
            print(data)


def print_list_verbose(objs: list[Any]) -> None:
    """Вывести список объектов в подробном режиме.

    Каждый объект выводится через `print_item(...)`.
    Между объектами печатается разделитель из 40 символов `-`.

    Args:
        objs: Список объектов для вывода.

    Returns:
        None
    """
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
    """Добавить стандартные аргументы для команды `list`.

    Добавляет:
    - `--offset` и `--limit` для пагинации;
    - `--order` для сортировки (с ограничением `order_choices`).

    Args:
        parser: Парсер команды `list`, куда добавляются аргументы.
        order_choices: Допустимые значения сортировки.
        default_order: Значение сортировки по умолчанию.

    Returns:
        None
    """
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
