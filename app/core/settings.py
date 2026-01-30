"""Настройки и подготовка runtime окружения.

Задачи модуля:
- единообразно вычислять DB_URL для CLI и GUI;
- подхватывать .env (если есть), но не быть зависимым от него;
- настраивать переменные окружения, которые важны для запуска из exe
  (например, MPLCONFIGDIR).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from app.core.paths import (
    build_sqlite_url,
    get_app_state_dir,
    get_default_db_path,
)

_ENV_LOADED = False


def is_frozen() -> bool:
    """Проверить, запущено ли приложение из упакованного exe.

    Returns:
        bool: True если запущено из PyInstaller/Nuitka, иначе False.
    """
    return bool(getattr(sys, 'frozen', False)) or hasattr(sys, '_MEIPASS')


def load_env_once() -> None:
    """Загрузить переменные окружения из .env один раз (если файл существует).

    Ищем .env:
    - в текущей директории (для разработки);
    - рядом с exe (для переносимого запуска).

    Returns:
        None
    """
    global _ENV_LOADED
    if _ENV_LOADED:
        return

    candidates = [
        Path.cwd() / '.env',
        Path(sys.executable).resolve().parent / '.env',
    ]

    for p in candidates:
        if p.exists():
            load_dotenv(str(p), override=False)
            break

    _ENV_LOADED = True


def get_db_url(*, override: Optional[str] = None) -> str:
    """Получить URL базы данных.

    Порядок выбора:
    1) override (если передан),
    2) переменная окружения DB_URL,
    3) (только в dev) ./inflation.db если файл существует,
    4) дефолт в каталоге состояния пользователя (APPDATA/...).

    Args:
        override: Явно заданный DB_URL.

    Returns:
        str: DB_URL для SQLAlchemy.
    """
    load_env_once()

    if override:
        return override

    env_url = os.getenv('DB_URL')
    if env_url:
        return env_url

    if not is_frozen():
        local_db = Path.cwd() / 'inflation.db'
        if local_db.exists():
            return build_sqlite_url(local_db)

    return build_sqlite_url(get_default_db_path())


def prepare_runtime_env(*, app_name: str = 'InflationTracker') -> None:
    """Подготовить окружение для корректной работы GUI/EXE.

    Сейчас важно:
    - MPLCONFIGDIR: matplotlib пишет кэш/настройки. В exe лучше направить
      это в writable каталог пользователя.

    Args:
        app_name: Имя приложения для каталога состояния.

    Returns:
        None
    """
    state_dir = get_app_state_dir(app_name)
    mpl_dir = state_dir / 'matplotlib'
    mpl_dir.mkdir(parents=True, exist_ok=True)

    os.environ.setdefault('MPLCONFIGDIR', str(mpl_dir))
