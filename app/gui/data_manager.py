# стало
"""Доступ к данным для GUI."""

from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.core.constants import (
    DATA_MANAGER_SIZE,
    DATA_MANAGER_TITLE,
)
from app.gui.tabs.categories import CategoriesTab
from app.gui.tabs.products import ProductsTab
from app.gui.tabs.purchases import PurchasesTab
from app.gui.tabs.stores import StoresTab
from app.gui.tabs.units import UnitsTab


class DataManagerDialog(QDialog):
    """Диалог управления справочниками и покупками.

    Вкладки строятся лениво: реальный виджет (со своим reload() в БД)
    создаётся только при первом переключении на вкладку, а не все разом
    при открытии диалога. Первая вкладка — исключение, она видна сразу,
    поэтому строится сразу, без отложенной подмены.
    """

    _TAB_FACTORIES: tuple[tuple[str, type], ...] = (
        ('Магазины', StoresTab),
        ('Категории', CategoriesTab),
        ('Единицы', UnitsTab),
        ('Продукты', ProductsTab),
        ('Покупки', PurchasesTab),
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(DATA_MANAGER_TITLE)
        self.resize(*DATA_MANAGER_SIZE)

        self.tabs = QTabWidget()
        self._pending: dict[int, type] = {}

        for index, (title, factory) in enumerate(self._TAB_FACTORIES):
            if index == 0:
                self.tabs.addTab(factory(), title)
            else:
                self.tabs.addTab(QWidget(), title)
                self._pending[index] = factory

        self.tabs.currentChanged.connect(self._on_tab_changed)

        btn_close = QPushButton('Закрыть')
        btn_close.clicked.connect(self.accept)

        bottom = QHBoxLayout()
        bottom.addStretch(1)
        bottom.addWidget(btn_close)

        layout = QVBoxLayout()
        layout.addWidget(self.tabs)
        layout.addLayout(bottom)
        self.setLayout(layout)

    def _on_tab_changed(self, index: int) -> None:
        """Строит реальную вкладку при первом переключении на неё.

        Args:
            index: Индекс вкладки, на которую переключились.

        Returns:
            None
        """
        factory = self._pending.pop(index, None)
        if factory is None:
            return

        title = self.tabs.tabText(index)

        self.tabs.blockSignals(True)
        try:
            self.tabs.removeTab(index)
            self.tabs.insertTab(index, factory(), title)
            self.tabs.setCurrentIndex(index)
        finally:
            self.tabs.blockSignals(False)
