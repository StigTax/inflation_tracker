"""Интеграционный тест на data-миграцию сида (a4ff3de9f63b).

Единственный тест в проекте, который реально гоняет alembic upgrade/
downgrade поверх файловой SQLite, а не строит схему через
Base.metadata.create_all(), как в tests/conftest.py. По-другому логику
upgrade()/downgrade() конкретной ревизии не проверить: она живёт в
файле миграции, а не в моделях, которые видит create_all().

Гоняем на настоящем файле (tmp_path), а не :memory: — потому что
именно с открытием файла всё и ломалось руками на Windows, и
:memory: тут бы эту категорию ошибок вообще не поймал.
"""

import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config
from app.core.migrations import upgrade_db
from app.core.paths import build_sqlite_url
from app.core.resources import resource_base_dir
from app.core.seed_csv import read_seed_rows

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SEED_DIR = resource_base_dir() / 'app' / 'data' / 'seed'
_SEED_REVISION = 'a4ff3de9f63b'
_PRE_SEED_REVISION = 'c27e1cbe927d'


def _expected(filename: str, columns: list, key_column: str) -> set:
    """Ожидаемый набор значений — берём из самого CSV, а не хардкодим.

    Иначе тест был бы завязан на конкретное содержимое seed-файлов,
    которое ты сам же и просил отредактировать под реальный список
    категорий/магазинов. Правильный инвариант — "что в CSV, то и в БД",
    а не "в БД лежит вот этот конкретный набор строк".
    """
    rows = read_seed_rows(
        _SEED_DIR / filename, required_columns=columns, key_column=key_column
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
    """Мини-аналог upgrade_db(), только для downgrade.

    В проде downgrade никогда не вызывается (это чисто dev-инструмент),
    поэтому не выношу его публичным API в app.core.migrations —
    достаточно локального helper'а для теста.
    """
    import os
    os.environ['DB_URL'] = db_url
    cfg = Config(str(_PROJECT_ROOT / 'alembic.ini'))
    cfg.set_main_option('sqlalchemy.url', db_url)
    command.downgrade(cfg, revision)


def test_seed_migration_inserts_rows_from_csv(tmp_path, monkeypatch):
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


def test_seed_migration_downgrade_removes_only_seeded_rows(
    tmp_path, monkeypatch
):
    db_path = tmp_path / 'seed_test.db'
    db_url = build_sqlite_url(db_path)
    monkeypatch.setenv('DB_URL', db_url)

    upgrade_db(db_url, revision=_SEED_REVISION)
    _downgrade(db_url, _PRE_SEED_REVISION)

    # Таблицы остаются (схема с предыдущей ревизии никуда не делась),
    # но строки сида — ровно те, что были вставлены, — исчезли.
    assert _rows(db_path, 'category', 'name') == set()
    assert _rows(db_path, 'store', 'name') == set()
    assert _rows(db_path, 'unit', 'unit') == set()


def test_seed_migration_is_idempotent_across_upgrades(tmp_path, monkeypatch):
    """upgrade head дважды подряд не должен пытаться вставить сид повторно.

    Это тот сценарий, который реально происходит на каждом старте
    приложения: ensure_db_schema() гоняет `alembic upgrade head` при
    КАЖДОМ запуске, а не только при первом. Если бы данные вставлялись
    не как одноразовая ревизия, а как часть upgrade()-логики, второй
    запуск упал бы на UNIQUE constraint по name.
    """
    db_path = tmp_path / 'seed_test.db'
    db_url = build_sqlite_url(db_path)
    monkeypatch.setenv('DB_URL', db_url)

    upgrade_db(db_url, revision=_SEED_REVISION)
    upgrade_db(db_url, revision=_SEED_REVISION)  # как второй запуск приложения

    assert _rows(db_path, 'category', 'name') == _expected(
        'categories.csv', ['name', 'description'], 'name'
    )
