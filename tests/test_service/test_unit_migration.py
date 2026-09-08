"""Регрессия миграции уникальности единиц измерения."""

import sqlite3

import pytest
from app.core.migrations import upgrade_db
from app.core.paths import build_sqlite_url

_PRE_UNIQUE_REVISION = 'a4ff3de9f63b'
_UNIQUE_REVISION = 'f6c8f1b2d3a4'


def test_unit_unique_migration_merges_duplicates_and_repoints_products(
    tmp_path, monkeypatch
):
    db_path = tmp_path / 'unit_unique.db'
    db_url = build_sqlite_url(db_path)
    monkeypatch.setenv('DB_URL', db_url)

    upgrade_db(db_url, revision=_PRE_UNIQUE_REVISION)

    conn = sqlite3.connect(db_path)
    try:
        keep_id = conn.execute(
            "SELECT id FROM unit WHERE unit='кг' ORDER BY id LIMIT 1"
        ).fetchone()[0]
        cursor = conn.execute(
            """
            INSERT INTO unit(measure_type, unit, to_create)
            VALUES ('ВЕС', 'КГ', CURRENT_TIMESTAMP)
            """
        )
        duplicate_id = cursor.lastrowid
        conn.execute(
            """
            INSERT INTO product(name, category_id, unit_id, to_create)
            VALUES ('Тестовый продукт с дублем', NULL, ?, CURRENT_TIMESTAMP)
            """,
            (duplicate_id,),
        )
        conn.commit()
    finally:
        conn.close()

    upgrade_db(db_url, revision=_UNIQUE_REVISION)

    conn = sqlite3.connect(db_path)
    try:
        unit_rows = conn.execute(
            "SELECT id, unit FROM unit WHERE lower(unit)='кг' ORDER BY id"
        ).fetchall()
        product_unit_id = conn.execute(
            """
            SELECT unit_id FROM product
            WHERE name='Тестовый продукт с дублем'
            """
        ).fetchone()[0]

        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """
                INSERT INTO unit(measure_type, unit, to_create)
                VALUES ('Вес', 'кг', CURRENT_TIMESTAMP)
                """
            )
    finally:
        conn.close()

    assert unit_rows == [(keep_id, 'кг')]
    assert product_unit_id == keep_id
