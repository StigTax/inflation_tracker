"""Виджет выбора набора товаров кликом, без ручного ввода ID.

Используется в аналитике и для "корзины" (basket_index — обязательный
непустой набор), и как опциональный фильтр товаров у "магазина"
(store_index). Список товаров, которые вообще можно добавить,
задаётся снаружи через set_available_products() — так виджет не знает
и не должен знать, откуда взялось ограничение (весь каталог или только
товары конкретного магазина), это забота вызывающего кода.
"""

from __future__ import annotations

from typing import Any, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.gui.qt_helpers import setup_searchable_combo

_ID_ROLE = Qt.ItemDataRole.UserRole


class ProductPickerWidget(QWidget):
    """Набор товаров: поиск+клик "Добавить", список уже выбранных ниже.

    Явно НЕ текстовое поле с ID через запятую — пользователь ищет товар
    по имени в комбобоксе (как и везде в приложении, через
    setup_searchable_combo), жмёт "+ Добавить", товар появляется в
    списке. Убрать — выделить строку и нажать "Убрать выбранное" или
    дважды кликнуть по строке.
    """

    changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self._selected: dict[int, str] = {}  # product_id -> label

        self._add_combo = QComboBox()
        setup_searchable_combo(
            self._add_combo, placeholder='Начни печатать продукт…'
        )

        self._btn_add = QPushButton('+ Добавить')
        self._btn_add.clicked.connect(self._on_add_clicked)

        top = QHBoxLayout()
        top.addWidget(self._add_combo, 1)
        top.addWidget(self._btn_add)

        self._list = QListWidget()
        self._list.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self._list.setMaximumHeight(96)
        self._list.itemDoubleClicked.connect(
            lambda item: self._remove_id(item.data(_ID_ROLE))
        )

        self._btn_remove = QPushButton('Убрать выбранное')
        self._btn_remove.clicked.connect(self._on_remove_clicked)

        bottom = QHBoxLayout()
        bottom.addStretch(1)
        bottom.addWidget(self._btn_remove)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(top)
        layout.addWidget(self._list)
        layout.addLayout(bottom)
        self.setLayout(layout)

    def set_available_products(self, products: list[Any]) -> None:
        """(Пере)заполняет комбобокс "что можно добавить".

        Товары, уже выбранные, но отсутствующие в новом списке (типичный
        случай — сменили магазин, и старый выбор для него не подходит),
        молча убираются из текущего выбора: список синхронизируется с
        новыми доступными вариантами, а не хранит "осиротевшие" ID.

        Args:
            products: Объекты с полями id/name (и опционально unit) —
                как правило, ORM Product.
        """
        current = self._add_combo.currentData()
        self._add_combo.clear()
        self._add_combo.addItem('— выбери продукт —', None)

        available_ids = set()
        for p in products:
            self._add_combo.addItem(self._format_label(p), p.id)
            available_ids.add(p.id)

        if current is not None:
            idx = self._add_combo.findData(current)
            if idx >= 0:
                self._add_combo.setCurrentIndex(idx)

        stale = set(self._selected) - available_ids
        for product_id in stale:
            self._remove_id(product_id, emit=False)
        if stale:
            self.changed.emit()

    @staticmethod
    def _format_label(product: Any) -> str:
        unit = getattr(product, 'unit', None)
        suffix = f' ({unit.measure_type} {unit.unit})' if unit else ''
        return f'{product.name}{suffix}'

    def _on_add_clicked(self) -> None:
        product_id = self._add_combo.currentData()
        if product_id is None or product_id in self._selected:
            return

        label = self._add_combo.currentText()
        self._selected[product_id] = label

        item = QListWidgetItem(label)
        item.setData(_ID_ROLE, product_id)
        self._list.addItem(item)

        self.changed.emit()

    def _on_remove_clicked(self) -> None:
        item = self._list.currentItem()
        if item is None:
            return
        self._remove_id(item.data(_ID_ROLE))

    def _remove_id(
        self, product_id: Optional[int], *, emit: bool = True
    ) -> None:
        if product_id is None or product_id not in self._selected:
            return

        self._selected.pop(product_id)
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item.data(_ID_ROLE) == product_id:
                self._list.takeItem(i)
                break

        if emit:
            self.changed.emit()

    def add_product_id(self, product_id: int) -> bool:
        """Добавляет товар по ID — как если бы его выбрали в комбобоксе
        и нажали "+ Добавить".

        Args:
            product_id: ID товара из текущего списка доступных
                (см. set_available_products()).

        Returns:
            bool: False, если такого ID нет среди доступных — товар не
                добавлен (и это не ошибка, просто нечего добавлять).
        """
        idx = self._add_combo.findData(product_id)
        if idx < 0:
            return False
        self._add_combo.setCurrentIndex(idx)
        self._on_add_clicked()
        return True

    def selected_ids(self) -> list[int]:
        """ID выбранных товаров, в порядке добавления."""
        return list(self._selected.keys())

    def clear(self) -> None:
        """Полностью очищает выбор (не трогает список "что доступно")."""
        if not self._selected:
            return
        self._selected.clear()
        self._list.clear()
        self.changed.emit()
