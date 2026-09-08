"""Резолв пути к забандленным read-only ресурсам приложения.

В отличие от app/core/paths.py (куда приложение сам ПИШЕТ — БД, логи),
этот модуль про то, откуда приложение ЧИТАЕТ то, что зашито в поставку:
alembic.ini/alembic/*, CSV с начальными справочниками и т.п.

Раньше это жило приватной функцией внутри migrations.py — вынесено
сюда, т.к. теперь этим же путём пользуется не только Alembic.
"""

from __future__ import annotations

import sys
from pathlib import Path


def resource_base_dir() -> Path:
    """Получить базовую директорию забандленных ресурсов проекта.

    В собранном PyInstaller-приложении (--onedir/--onefile) все файлы,
    добавленные через --add-data, распаковываются в sys._MEIPASS.
    Из исходников (dev-режим, editable install) это просто корень
    репозитория.

    Returns:
        Path: Директория, где лежат alembic.ini, alembic/, app/data/...
    """
    if hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS).resolve()
    return Path(__file__).resolve().parents[2]
