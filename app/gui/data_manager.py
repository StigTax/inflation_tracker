'''Доступ к данным для GUI.'''

from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
)

from app.gui.tabs.categories import CategoriesTab
from app.gui.tabs.products import ProductsTab
from app.gui.tabs.purchases import PurchasesTab
from app.gui.tabs.stores import StoresTab
from app.gui.tabs.units import UnitsTab


class DataManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Данные')
        self.resize(1000, 650)

        tabs = QTabWidget()
        tabs.addTab(StoresTab(), 'Магазины')
        tabs.addTab(CategoriesTab(), 'Категории')
        tabs.addTab(UnitsTab(), 'Единицы')
        tabs.addTab(ProductsTab(), 'Продукты')
        tabs.addTab(PurchasesTab(), 'Покупки')

        btn_close = QPushButton('Закрыть')
        btn_close.clicked.connect(self.accept)

        bottom = QHBoxLayout()
        bottom.addStretch(1)
        bottom.addWidget(btn_close)

        layout = QVBoxLayout()
        layout.addWidget(tabs)
        layout.addLayout(bottom)
        self.setLayout(layout)
