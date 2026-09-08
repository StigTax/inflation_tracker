"""Bootstrap приложения: инициализация БД и миграций."""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.engine import make_url

from app.core import db as db_module
from app.core.db import init_db
from app.core.migrations import ensure_db_schema

logger = logging.getLogger(__name__)


def init_app(
    *,
    db_url: Optional[str] = None,
) -> str:
    """Инициализировать БД и привести схему к актуальной ревизии.

    Логирование настраивается entry point до вызова этой функции.

    Args:
        db_url: Явно заданный DB_URL. Если None — берётся из env или default.

    Returns:
        str: Фактический DB_URL, с которым инициализирована БД.
    """
    init_db(db_url)
    url = db_module.DB_URL

    if url and ':memory:' not in url:
        ensure_db_schema(url)

    safe_url = make_url(url).render_as_string(hide_password=True)
    logger.info('База данных готова: %s', safe_url)
    return url
