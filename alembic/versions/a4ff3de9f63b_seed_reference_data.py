"""Сид данные: категории, единицы измерения, магазины по умолчанию

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

_SEED_DIR = resource_base_dir() / 'app' / 'data' / 'seed'

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


def upgrade() -> None:
    """Наполнить category/unit/store стартовыми данными из CSV.

    Одноразовая data-миграция: применяется вместе со схемой ровно один
    раз на каждую БД (Alembic сам трекает это в alembic_version), так
    что дальнейшее удаление/правка справочников пользователем этой
    миграцией на следующих запусках НЕ перезатирается.

    Вставка через op.bulk_insert() по "облегчённым" sa.table(...), а не
    через ORM-модели app.models.*: миграция не должна зависеть от того,
    как выглядят модели сегодня — она обязана остаться рабочей и после
    того, как модели изменятся. to_create проставляем вручную: у
    PreBase.to_create default выставлен на уровне Python (ORM), а не
    на уровне БД (server_default), поэтому "облегчённая" table его не
    подхватит сама.
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

    now = datetime.now(timezone.utc)

    categories = _read_categories()
    if categories:
        op.bulk_insert(category, [
            {
                'name': row['name'],
                'description': row['description'] or None,
                'to_create': now,
            }
            for row in categories
        ])

    units = _read_units()
    if units:
        op.bulk_insert(unit, [
            {
                'measure_type': row['measure_type'],
                'unit': row['unit'],
                'to_create': now,
            }
            for row in units
        ])

    stores = _read_stores()
    if stores:
        op.bulk_insert(store, [
            {
                'name': row['name'],
                'description': row['description'] or None,
                'to_create': now,
            }
            for row in stores
        ])


def downgrade() -> None:
    """Удалить ровно те строки, что были добавлены в upgrade(), по имени.

    ВАЖНО: и upgrade(), и downgrade() читают CSV заново при каждом
    запуске, а не хранят снимок вставленных значений внутри самой
    миграции. Это значит: если content категорий/units/stores.csv
    поменяется ПОСЛЕ того, как эта миграция где-то уже была применена,
    поведение upgrade/downgrade для тех БД задним числом изменится.
    Для личного pet-проекта это осознанный компромисс (одна копия
    правды, переиспользуемая будущим CSV-импортом), но если это
    когда-нибудь станет проблемой — правильный путь не редактировать
    эти CSV, а добавлять новую data-миграцию поверх.
    """
    conn = op.get_bind()

    category = sa.table('category', sa.column('name', sa.String))
    unit = sa.table('unit', sa.column('unit', sa.String))
    store = sa.table('store', sa.column('name', sa.String))

    categories = _read_categories()
    if categories:
        conn.execute(
            category.delete().where(
                category.c.name.in_([row['name'] for row in categories])
            )
        )

    units = _read_units()
    if units:
        conn.execute(
            unit.delete().where(
                unit.c.unit.in_([row['unit'] for row in units])
            )
        )

    stores = _read_stores()
    if stores:
        conn.execute(
            store.delete().where(
                store.c.name.in_([row['name'] for row in stores])
            )
        )
