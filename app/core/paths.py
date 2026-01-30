"""Утилиты путей приложения.

Модуль нужен, чтобы приложение одинаково работало:
- из исходников (во время разработки);
- после упаковки в exe (PyInstaller/Nuitka);
- на других компьютерах (разные каталоги, права доступа).

Идея простая: всё, что приложение **пишет** (логи, sqlite БД),
должно лежать в пользовательском каталоге, а не рядом с исходниками.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

_DEFAULT_APP_NAME = 'InflationTracker'


def get_app_state_dir(app_name: Optional[str] = None) -> Path:
    """Получить каталог состояния приложения (пишем сюда логи/БД).

    В Windows используется `%APPDATA%`, в macOS —
    `~/Library/Application Support`, в Linux — `$XDG_STATE_HOME`
    или `~/.local/state`.

    Args:
        app_name: Имя приложения для каталога. Если не задано — используется
            внутреннее значение по умолчанию.

    Returns:
        Path: Путь к каталогу состояния приложения.
    """
    name = app_name or _DEFAULT_APP_NAME

    if os.name == 'nt':
        base = os.getenv('APPDATA')
        base_dir = Path(base) if base else Path.home() / 'AppData' / 'Roaming'
    elif sys.platform == 'darwin':
        base_dir = Path.home() / 'Library' / 'Application Support'
    else:
        base = os.getenv('XDG_STATE_HOME')
        base_dir = Path(base) if base else Path.home() / '.local' / 'state'

    path = base_dir / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_logs_dir(app_name: Optional[str] = None) -> Path:
    """Получить каталог логов и гарантировать его существование.

    Args:
        app_name: Имя приложения для каталога.

    Returns:
        Path: Путь к каталогу логов.
    """
    path = get_app_state_dir(app_name) / 'logs'
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_default_db_path(app_name: Optional[str] = None) -> Path:
    """Получить путь к sqlite базе по умолчанию.

    Args:
        app_name: Имя приложения для каталога.

    Returns:
        Path: Абсолютный путь к файлу базы данных.
    """
    return get_app_state_dir(app_name) / 'inflation.db'


def build_sqlite_url(db_path: Path) -> str:
    """Собрать SQLAlchemy URL для sqlite по абсолютному пути.

    Args:
        db_path: Путь к файлу базы данных.

    Returns:
        str: URL для SQLAlchemy вида `sqlite+pysqlite:///...`.
    """
    p = db_path.expanduser().resolve()
    return f'sqlite+pysqlite:///{p.as_posix()}'
