"""Настройка логирования приложения."""

from __future__ import annotations

import logging
import sys
from datetime import date
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from app.core.constants import (
    APP_NAME,
    BLUE,
    DT_FORMAT,
    GREEN,
    LOG_FORMAT,
    LOG_ROTATE_BACKUP_COUNT,
    LOG_ROTATE_MAX_BYTES,
    RED,
    RESET,
    YELLOW,
)
from app.core.paths import get_logs_dir


class ColoredConsoleHandler(logging.StreamHandler):
    """Хендлер для цветного вывода в консоль."""

    COLOR_MAP = {
        logging.CRITICAL: RED,
        logging.ERROR: RED,
        logging.WARNING: YELLOW,
        logging.INFO: GREEN,
        logging.DEBUG: BLUE,
    }

    def emit(self, record):
        try:
            message = self.format(record)
            color = self.COLOR_MAP.get(record.levelno, RESET)
            self.stream.write(f'{color}{message}{RESET}\n')
            self.flush()
        except Exception:
            self.handleError(record)


def configure_logging(
    *,
    log_level: int = logging.DEBUG,
    console_level: int = logging.INFO,
    enable_console: Optional[bool] = None,
    log_dir: Optional[Path] = None,
) -> Path:
    """Настроить корневое логирование приложения.

    В GUI/EXE консоль может отсутствовать (sys.stderr=None), поэтому
    консольный хендлер включается только когда это безопасно.

    Args:
        log_level: Уровень логов для файла.
        console_level: Уровень логов для консоли.
        enable_console: Явно включить/выключить консольный хендлер. Если
            `None`, включается автоматически при доступном `sys.stderr`.
        log_dir: Каталог логов. Если `None`, используется каталог состояния
            пользователя через `get_logs_dir()`.

    Returns:
        Path: Путь к текущему файлу логов.
    """
    root = logging.getLogger()
    root.setLevel(log_level)

    if root.handlers:
        root.handlers.clear()

    logging.captureWarnings(True)

    log_dir = get_logs_dir(APP_NAME) if log_dir is None else Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / f'logs_to_{date.today().isoformat()}.log'

    formatter = logging.Formatter(LOG_FORMAT, datefmt=DT_FORMAT)

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=LOG_ROTATE_MAX_BYTES,
        backupCount=LOG_ROTATE_BACKUP_COUNT,
        encoding='utf-8',
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    if enable_console is None:
        enable_console = sys.stderr is not None and hasattr(
            sys.stderr, 'write'
        )

    if enable_console:
        console_handler = ColoredConsoleHandler(stream=sys.stderr)
        console_handler.setLevel(console_level)
        console_handler.setFormatter(formatter)
        root.addHandler(console_handler)

    return log_file
