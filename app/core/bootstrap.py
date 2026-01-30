"""Bootstrap приложения: логирование + БД + миграции.

Цель: единая точка старта для CLI и GUI, чтобы не было рассинхрона в том,
какую БД открываем, где логи, и когда накатываем миграции.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from app.core.config_log import configure_logging
from app.core.constants import DB_URL_ENV_VAR, DEFAULT_DB_URL
from app.core.db import init_db
from app.core.migrations import ensure_db_schema


def init_app(
    *,
    enable_console_logs: bool,
    db_url: Optional[str] = None,
    log_dir: Optional[Path] = None,
) -> str:
    """Инициализировать приложение: логирование, БД и миграции.

    Args:
        enable_console_logs: Включить вывод в консоль (CLI=True, GUI=False).
        db_url: Явно заданный DB_URL. Если None — берётся из env или default.
        log_dir: Каталог логов. Если None — дефолтный (APPDATA/.../logs).

    Returns:
        str: Фактический DB_URL, с которым инициализирована БД.
    """
    configure_logging(enable_console=enable_console_logs, log_dir=log_dir)

    url = db_url or os.getenv(DB_URL_ENV_VAR, DEFAULT_DB_URL)
    init_db(url)

    if ':memory:' not in url:
        ensure_db_schema(url)

    return url
