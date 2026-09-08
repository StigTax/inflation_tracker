"""Интеграционные тесты data-миграции стартовых справочников."""

import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config
from app.core.migrations import upgrade_db
from app.core.paths import build_sqlite_url
from app.core.resources import resource_base_dir
from app.core.seed_csv import read_seed_rows

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SEED_REVISION = 'a4ff3de9f63b'
_PRE_SEED_REVISION = 'c27e1cbe927d'
_SEED_DIR = resource_base_dir() / 'alembic' / 'data' / _SEED_REVISION


def _expected(filename: str, columns: list, key_column: str) -> set:
    rows = read_seed_rows(
        _SEED_DIR / filename,
        required_columns=columns,
        key_column=key_column,
    )
    return {row[key_column] for row in rows}


def _rows(db_path: Path, table: str, column: str) -> set:
    conn = sqlite3.connect(db_path)
    try:
        return {
            row[0] for row in conn.execute(f'SELECT {column} FROM {table}')
        }
    finally:
        conn.close()


def _downgrade(db_url: str, revision: str) -> None:
    import os

    os.environ['DB_URL'] = db_url
    cfg = Config(str(_PROJECT_ROOT / 'alembic.ini'))
    cfg.set_main_option('sqlalchemy.url', db_url)
    command.downgrade(cfg, revision)


def test_seed_migration_inserts_rows_from_revision_snapshot(
    tmp_path, monkeypatch
):
    db_path = tmp_path / 'seed_test.db'
    db_url = build_sqlite_url(db_path)
    monkeypatch.setenv('DB_URL', db_url)

    upgrade_db(db_url, revision=_SEED_REVISION)

    assert _rows(db_path, 'category', 'name') == _expected(
        'categories.csv', ['name', 'description'], 'name'
    )
    assert _rows(db_path, 'store', 'name') == _expected(
        'stores.csv', ['name', 'description'], 'name'
    )
    assert _rows(db_path, 'unit', 'unit') == _expected(
        'units.csv', ['measure_type', 'unit'], 'unit'
    )


def test_seed_migration_downgrade_keeps_reference_data(
    tmp_path, monkeypatch
):
    """Downgrade не должен рисковать пользовательскими справочниками."""
    db_path = tmp_path / 'seed_test.db'
    db_url = build_sqlite_url(db_path)
    monkeypatch.setenv('DB_URL', db_url)

    upgrade_db(db_url, revision=_SEED_REVISION)
    before = _rows(db_path, 'category', 'name')

    _downgrade(db_url, _PRE_SEED_REVISION)

    assert _rows(db_path, 'category', 'name') == before


def test_seed_migration_is_idempotent_across_upgrades(tmp_path, monkeypatch):
    db_path = tmp_path / 'seed_test.db'
    db_url = build_sqlite_url(db_path)
    monkeypatch.setenv('DB_URL', db_url)

    upgrade_db(db_url, revision=_SEED_REVISION)
    upgrade_db(db_url, revision=_SEED_REVISION)

    assert _rows(db_path, 'category', 'name') == _expected(
        'categories.csv', ['name', 'description'], 'name'
    )


def test_seed_migration_skips_existing_reference_rows(
    tmp_path, monkeypatch
):
    """Upgrade старой заполненной БД не падает на совпадениях seed."""
    db_path = tmp_path / 'seed_existing.db'
    db_url = build_sqlite_url(db_path)
    monkeypatch.setenv('DB_URL', db_url)

    upgrade_db(db_url, revision=_PRE_SEED_REVISION)

    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            INSERT INTO category(name, description, to_create)
            VALUES ('Молочные продукты', 'Пользовательское описание',
                    CURRENT_TIMESTAMP)
            """
        )
        conn.execute(
            """
            INSERT INTO store(name, description, to_create)
            VALUES ('Пятёрочка', 'Мой магазин', CURRENT_TIMESTAMP)
            """
        )
        conn.execute(
            """
            INSERT INTO unit(measure_type, unit, to_create)
            VALUES ('Вес', 'кг', CURRENT_TIMESTAMP)
            """
        )
        conn.commit()
    finally:
        conn.close()

    upgrade_db(db_url, revision=_SEED_REVISION)

    conn = sqlite3.connect(db_path)
    try:
        category = conn.execute(
            "SELECT description FROM category WHERE name='Молочные продукты'"
        ).fetchall()
        store = conn.execute(
            "SELECT description FROM store WHERE name='Пятёрочка'"
        ).fetchall()
        units = conn.execute("SELECT id FROM unit WHERE unit='кг'").fetchall()
    finally:
        conn.close()

    assert category == [('Пользовательское описание',)]
    assert store == [('Мой магазин',)]
    assert len(units) == 1
