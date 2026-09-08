"""Сид данные: категории, единицы измерения, магазины по умолчанию.

Revision ID: a4ff3de9f63b
Revises: c27e1cbe927d
Create Date: 2026-09-08 00:00:00.000000

"""
from datetime import datetime, timezone
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.core.resources import resource_base_dir
from app.core.seed_csv import read_seed_rows

# revision identifiers, used by Alembic.
revision: str = 'a4ff3de9f63b'
down_revision: Union[str, Sequence[str], None] = 'c27e1cbe927d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Снимок данных привязан к конкретной ревизии. Текущие app/data/seed/*.csv
# можно менять для будущих релизов, не меняя задним числом поведение этой
# уже опубликованной миграции.
_SEED_DIR = resource_base_dir() / 'alembic' / 'data' / revision

_CATEGORY_COLUMNS = ['name', 'description']
_UNIT_COLUMNS = ['measure_type', 'unit']
_STORE_COLUMNS = ['name', 'description']


def _read_categories() -> list[dict]:
    return read_seed_rows(
        _SEED_DIR / 'categories.csv',
        required_columns=_CATEGORY_COLUMNS,
        key_column='name',
    )


def _read_units() -> list[dict]:
    return read_seed_rows(
        _SEED_DIR / 'units.csv',
        required_columns=_UNIT_COLUMNS,
        key_column='unit',
    )


def _read_stores() -> list[dict]:
    return read_seed_rows(
        _SEED_DIR / 'stores.csv',
        required_columns=_STORE_COLUMNS,
        key_column='name',
    )


def _missing_rows(
    conn,
    table: sa.TableClause,
    key_column: str,
    rows: list[dict],
) -> list[dict]:
    """Вернуть только строки, natural key которых ещё нет в БД.

    Сравнение выполняется через casefold() в Python. Это даёт одинаковое
    поведение для SQLite и кириллицы, где SQL lower() зависит от collation.
    """
    if not rows:
        return []

    column = table.c[key_column]
    existing = {
        str(value).strip().casefold()
        for value in conn.execute(sa.select(column)).scalars()
        if value is not None
    }
    return [
        row
        for row in rows
        if str(row[key_column]).strip().casefold() not in existing
    ]


def upgrade() -> None:
    """Добавить только отсутствующие стартовые справочники.

    На новой БД будут добавлены все строки snapshot CSV. На существующей
    БД уже созданные пользователем категории/единицы/магазины сохраняются,
    а совпадающие natural keys не приводят к UNIQUE-ошибке при обновлении.
    """
    category = sa.table(
        'category',
        sa.column('name', sa.String),
        sa.column('description', sa.Text),
        sa.column('to_create', sa.DateTime),
    )
    unit = sa.table(
        'unit',
        sa.column('measure_type', sa.String),
        sa.column('unit', sa.String),
        sa.column('to_create', sa.DateTime),
    )
    store = sa.table(
        'store',
        sa.column('name', sa.String),
        sa.column('description', sa.Text),
        sa.column('to_create', sa.DateTime),
    )

    conn = op.get_bind()
    now = datetime.now(timezone.utc)

    categories = _missing_rows(conn, category, 'name', _read_categories())
    if categories:
        op.bulk_insert(
            category,
            [
                {
                    'name': row['name'],
                    'description': row['description'] or None,
                    'to_create': now,
                }
                for row in categories
            ],
        )

    units = _missing_rows(conn, unit, 'unit', _read_units())
    if units:
        op.bulk_insert(
            unit,
            [
                {
                    'measure_type': row['measure_type'],
                    'unit': row['unit'],
                    'to_create': now,
                }
                for row in units
            ],
        )

    stores = _missing_rows(conn, store, 'name', _read_stores())
    if stores:
        op.bulk_insert(
            store,
            [
                {
                    'name': row['name'],
                    'description': row['description'] or None,
                    'to_create': now,
                }
                for row in stores
            ],
        )


def downgrade() -> None:
    """Не удалять справочные данные при downgrade.

    После поддержки upgrade поверх уже заполненной пользовательской БД
    миграция не может надёжно отличить строки, которые вставила сама, от
    существовавших ранее строк с теми же natural keys. Удалять их было бы
    потенциальной потерей пользовательских данных, поэтому data-часть
    ревизии намеренно необратима.
    """
    return None
