"""Точка входа GUI."""

from __future__ import annotations

import logging
import sys
import traceback

from PyQt6.QtCore import QtMsgType, qInstallMessageHandler
from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox

from app.core.bootstrap import init_app
from app.core.config_log import configure_logging
from app.core.constants import (
    MAIN_WINDOW_SIZE,
    MAIN_WINDOW_TITLE,
)
from app.core.settings import prepare_runtime_env

logger = logging.getLogger(__name__)


def _install_qt_log_handler() -> None:
    """Перекинуть сообщения Qt в логгер Python.

    Returns:
        None
    """

    def _handler(
        mode: QtMsgType,
        context,
        message: str
    ) -> None:  # noqa: ANN001
        if mode == QtMsgType.QtDebugMsg:
            logger.debug('Qt: %s', message)
            return
        if mode == QtMsgType.QtInfoMsg:
            logger.info('Qt: %s', message)
            return
        if mode == QtMsgType.QtWarningMsg:
            logger.warning('Qt: %s', message)
            return
        if mode == QtMsgType.QtCriticalMsg:
            logger.error('Qt: %s', message)
            return
        if mode == QtMsgType.QtFatalMsg:
            logger.critical('Qt: %s', message)
            return

    qInstallMessageHandler(_handler)


def _install_excepthook(app: QApplication, *, log_file_path: str) -> None:
    """Подключить глобальный обработчик необработанных исключений.

    Args:
        app: Экземпляр QApplication.
        log_file_path: Путь к файлу логов.

    Returns:
        None
    """

    def _hook(exc_type, exc, tb) -> None:  # noqa: ANN001
        text = ''.join(traceback.format_exception(exc_type, exc, tb))
        logger.critical('Unhandled exception:\n%s', text)

        box = QMessageBox()
        box.setIcon(QMessageBox.Icon.Critical)
        box.setWindowTitle('Ошибка приложения')
        box.setText('Произошла непредвиденная ошибка. Подробности в логах.')
        box.setInformativeText(f'Файл логов: {log_file_path}')
        box.setDetailedText(text)
        box.exec()

        app.quit()

    sys.excepthook = _hook


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(MAIN_WINDOW_TITLE)
        self.resize(*MAIN_WINDOW_SIZE)

        from app.gui.analytics import AnalyticsWidget

        self.setCentralWidget(AnalyticsWidget())


def main() -> None:
    log_file = configure_logging(enable_console=False)

    prepare_runtime_env()

    app = QApplication(sys.argv)
    _install_qt_log_handler()
    _install_excepthook(app, log_file_path=str(log_file))

    try:
        init_app(enable_console_logs=False)
    except Exception:
        logger.exception('Не удалось инициализировать БД')

        box = QMessageBox()
        box.setIcon(QMessageBox.Icon.Critical)
        box.setWindowTitle('Ошибка базы данных')
        box.setText(
            'Не удалось подготовить базу данных для работы приложения.'
        )
        box.setInformativeText(f'Проверь логи: {log_file}')
        box.exec()
        return

    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
