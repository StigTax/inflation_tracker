"""Сделать обозначение единицы измерения уникальным.

Revision ID: f6c8f1b2d3a4
Revises: a4ff3de9f63b
Create Date: 2026-09-09 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'f6c8f1b2d3a4'
down_revision: Union[str, Sequence[str], None] = 'a4ff3de9f63b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _deduplicate_units() -> None:
    """Слить дубли Unit и перепривязать продукты к первой записи.

    Сравнение регистронезависимое через casefold(), чтобы старые данные
    вида ``кг``/``КГ`` тоже не мешали добавлению UNIQUE constraint.
    """
    conn = op.get_bind()
    rows = conn.execute(
        sa.text('SELECT id, unit FROM unit ORDER BY id ASC')
    ).all()

    keep_by_key: dict[str, int] = {}
    for unit_id, unit_value in rows:
        key = str(unit_value).strip().casefold()
        keep_id = keep_by_key.get(key)
        if keep_id is None:
            keep_by_key[key] = unit_id
            continue

        conn.execute(
            sa.text(
                'UPDATE product SET unit_id = :keep_id '
                'WHERE unit_id = :duplicate_id'
            ),
            {'keep_id': keep_id, 'duplicate_id': unit_id},
        )
        conn.execute(
            sa.text('DELETE FROM unit WHERE id = :duplicate_id'),
            {'duplicate_id': unit_id},
        )


def upgrade() -> None:
    _deduplicate_units()
    with op.batch_alter_table('unit') as batch_op:
        batch_op.create_unique_constraint('uq_unit_unit', ['unit'])


def downgrade() -> None:
    with op.batch_alter_table('unit') as batch_op:
        batch_op.drop_constraint('uq_unit_unit', type_='unique')
