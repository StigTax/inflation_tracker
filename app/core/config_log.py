import logging
from logging.handlers import RotatingFileHandler

from app.core.constants import (
    LOG_FILE, LOG_FORMAT, DT_FORMAT, LOG_DIR,
    RED, GREEN, YELLOW, BLUE, RESET
)


class ColoredConsoleHandler(logging.StreamHandler):
    """Хендлер для цветного вывода в консоль."""
    COLOR_MAP = {
        logging.CRITICAL: RED,
        logging.ERROR: RED,
        logging.WARNING: YELLOW,
        logging.INFO: GREEN,
        logging.DEBUG: BLUE
    }

    def emit(self, record):
        try:
            message = self.format(record)
            color = self.COLOR_MAP.get(record.levelno, RESET)
            self.stream.write(f"{color}{message}{RESET}\n")
            self.flush()
        except Exception:
            self.handleError(record)


def configure_logging():
    """Настройка логгера приложения."""
    log_dir = LOG_DIR
    log_dir.mkdir(exist_ok=True)
    log_file = LOG_FILE

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        logger.handlers.clear()

    formatter = logging.Formatter(
        LOG_FORMAT, datefmt=DT_FORMAT
    )

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 ** 6,
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    console_handler = ColoredConsoleHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
