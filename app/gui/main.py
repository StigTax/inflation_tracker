from __future__ import annotations

import os
import sys

from PyQt6.QtWidgets import QApplication, QMainWindow, QTabWidget

from app.core.db import init_db
from app.gui.tabs.categories import CategoriesTab
from app.gui.tabs.products import ProductsTab
from app.gui.tabs.purchases import PurchasesTab
from app.gui.tabs.stores import StoresTab
from app.gui.tabs.units import UnitsTab


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Inflation Tracker')
        self.resize(1000, 650)

        tabs = QTabWidget()
        tabs.addTab(StoresTab(), 'Магазины')
        tabs.addTab(CategoriesTab(), 'Категории')
        tabs.addTab(UnitsTab(), 'Единицы измерения')
        tabs.addTab(ProductsTab(), "Продукты")
        tabs.addTab(PurchasesTab(), 'Покупки')

        self.setCentralWidget(tabs)


def main() -> None:
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    init_db(os.getenv('DB_URL', 'sqlite+pysqlite:///./inflation.db'))
    main()
