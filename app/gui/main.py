'''Точка входа GUI.'''

from __future__ import annotations

import os
import sys

from PyQt6.QtWidgets import QApplication, QMainWindow

from app.core.db import init_db
from app.gui.analytics import AnalyticsWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Inflation Tracker')
        self.resize(1100, 700)

        self.setCentralWidget(AnalyticsWidget())


def main() -> None:
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    init_db(os.getenv('DB_URL', 'sqlite+pysqlite:///./inflation.db'))
    main()
