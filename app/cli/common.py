from __future__ import annotations

import os
from contextlib import contextmanager
from datetime import date
from typing import Any, Optional

from sqlalchemy.exc import IntegrityError

from app.core.db import init_db, get_session


def configure_db(
    db_url: Optional[str] = None,
    echo_sql: bool = False
) -> None:
    url = db_url or os.getenv(
        'DB_URL',
        'sqlite+pysqlite:///./inflation.db'
    )
    init_db(url, echo=echo_sql)


def parse_date(value: str) -> date:
    try:
        value = date.fromisoformat(value)
    except ValueError:
        raise ValueError(
            f'Неверный формат даты: {value}. '
            'Ожидается формат ГГГГ-ММ-ДД.'
        )
    return value


def print_item(obj: Any) -> None:
    data = obj.to_dict()
    for key, value in data.items():
        print(f'{key}: {value}')


def print_list_items(objs: list[Any]) -> None:
    for obj in objs:
        data = obj.to_dict()
        if 'id' in data and 'name' in data:
            print(f'{data["id"]}\t{data["name"]}')
        else:
            print(data)


@contextmanager
def session_scope():
    with get_session() as session:
        try:
            yield session
        except IntegrityError as e:
            session.rollback()
            raise RuntimeError(
                'Конфликт уникальности / целостности данных'
            ) from e
        except Exception:
            session.rollback()
            raise
