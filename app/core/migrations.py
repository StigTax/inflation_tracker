"""Утилиты миграций базы данных (Alembic)."""

from __future__ import annotations

import logging
import logging.config
import os
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

logger = logging.getLogger(__name__)


def _resource_base_dir() -> Path:
    """Получить базовую директорию ресурсов проекта.

    Returns:
        Path: Директория, где лежат alembic.ini и папка alembic.
    """
    if hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS).resolve()
    return Path(__file__).resolve().parents[2]


def _alembic_ini_path() -> Path:
    """Получить путь к alembic.ini.

    Returns:
        Path: Абсолютный путь к alembic.ini.
    """
    return _resource_base_dir() / 'alembic.ini'


def ensure_db_schema(db_url: str) -> None:
    """Гарантировать наличие схемы БД.

    Если база пустая (нет ключевой таблицы purchase), применяются миграции.

    Args:
        db_url: URL подключения SQLAlchemy.

    Raises:
        RuntimeError: Если применить миграции не удалось.
    """
    engine = create_engine(
        db_url,
        connect_args=(
            {'check_same_thread': False} if db_url.startswith('sqlite') else {}
        ),
        future=True,
    )

    inspector = inspect(engine)
    if inspector.has_table('purchase'):
        return

    logger.warning(
        'База данных не инициализирована (нет таблицы purchase). '
        'Применяю миграции Alembic...'
    )
    upgrade_db(db_url)


def upgrade_db(db_url: str, *, revision: str = 'head') -> None:
    """Применить миграции Alembic.

    Args:
        db_url: URL подключения SQLAlchemy.
        revision: Целевая ревизия Alembic (по умолчанию head).

    Raises:
        RuntimeError: Если alembic.ini не найден или миграции упали.
    """
    try:
        import app.core.base  # noqa: F401
    except Exception:
        logger.exception(
            'Не удалось импортировать app.core.base перед миграциями'
        )
        raise

    ini_path = _alembic_ini_path()
    if not ini_path.exists():
        raise RuntimeError(f'Не найден alembic.ini: {ini_path}')

    os.environ['DB_URL'] = db_url

    cfg = Config(str(ini_path))
    cfg.set_main_option('sqlalchemy.url', db_url)

    try:
        command.upgrade(cfg, revision)
        logger.info('Миграции Alembic применены: %s', revision)
    except Exception as e:
        raise RuntimeError('Не удалось применить миграции Alembic.') from e
