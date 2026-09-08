"""Пакетный ввод покупок: одна дата и магазин на всех, много строк товаров.

Идея: обычно покупка — это чек из нескольких товаров одного магазина,
одной датой. Заполнять для каждого товара отдельный PurchaseDialog
(дата+магазин заново на каждый) — раздражающе избыточно. Здесь дата и
магазин выбираются один раз, а строки товаров добавляются/удаляются
динамически.

Quick-add нового продукта сделан переиспользованием уже существующего
ProductDialog (app/gui/tabs/products.py), а не написанием второго
диалога создания продукта с нуля.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import QDate, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.crud import product_crud, store_crud
from app.gui.qt_helpers import setup_searchable_combo
from app.gui.ref_cache import get_cached, invalidate
from app.gui.tabs.common import list_items_safe, set_combo_by_data
from app.gui.tabs.products import ProductDialog
from app.models import Product
from app.service.crud_service import create_item


class BatchRowWidget(QWidget):
    """Одна строка партии: продукт + количество + сумма + комментарий."""

    remove_requested = pyqtSignal(object)  # emits self

    def __init__(
        self,
        parent=None,
        *,
        product_id: Optional[int] = None,
        quantity: Optional[float] = None,
        price: Optional[float] = None,
    ):
        super().__init__(parent)

        self.product_combo = QComboBox()
        setup_searchable_combo(
            self.product_combo, placeholder='Начни печатать продукт…'
        )
        self.reload_products()
        if product_id is not None:
            set_combo_by_data(self.product_combo, product_id)

        self.quantity_spin = QDoubleSpinBox()
        self.quantity_spin.setDecimals(3)
        self.quantity_spin.setRange(0.001, 1_000_000)
        self.quantity_spin.setValue(quantity if quantity is not None else 1.0)

        self.price_spin = QDoubleSpinBox()
        self.price_spin.setDecimals(2)
        self.price_spin.setRange(0.01, 1_000_000_000)
        self.price_spin.setValue(price if price is not None else 0.01)

        self.comment_edit = QLineEdit()
        self.comment_edit.setPlaceholderText('Комментарий (необязательно)')

        self.btn_remove = QPushButton('✕')
        self.btn_remove.setFixedWidth(28)
        self.btn_remove.setToolTip('Убрать строку')
        self.btn_remove.clicked.connect(
            lambda: self.remove_requested.emit(self)
        )

        row = QHBoxLayout()
        row.addWidget(self.product_combo, 3)
        row.addWidget(self.quantity_spin, 1)
        row.addWidget(self.price_spin, 1)
        row.addWidget(self.comment_edit, 2)
        row.addWidget(self.btn_remove)
        row.setContentsMargins(0, 0, 0, 0)
        self.setLayout(row)

    def reload_products(self) -> None:
        """(Пере)заполняет комбобокс продуктов из кэша.

        Вызывается и при создании строки, и после quick-add нового
        продукта — чтобы свежесозданный товар сразу появился во ВСЕХ
        уже открытых строках партии, а не только в той, где его
        затребовали.
        """
        current = self.product_combo.currentData()
        self.product_combo.clear()
        self.product_combo.addItem('— выбери продукт —', None)
        for p in get_cached(
            'products', lambda: list_items_safe(product_crud, limit=5000)
        ):
            label = f'{p.name} ({p.unit.measure_type} {p.unit.unit})'
            self.product_combo.addItem(label, p.id)
        if current is not None:
            set_combo_by_data(self.product_combo, current)

    def is_empty(self) -> bool:
        """Строка считается пустой, пока в ней не выбран продукт."""
        return self.product_combo.currentData() is None

    def values(self) -> Optional[Dict[str, Any]]:
        """Данные строки для create_purchases_batch().

        Returns:
            dict с product_id/quantity/price/comment, либо None для
            пустой строки (без выбранного продукта) — такие строки
            молча пропускаются при сохранении, чтобы не заставлять
            руками удалять "лишние" пустые строки перед сохранением.
        """
        product_id = self.product_combo.currentData()
        if product_id is None:
            return None
        return {
            'product_id': int(product_id),
            'quantity': float(self.quantity_spin.value()),
            'price': float(self.price_spin.value()),
            'comment': self.comment_edit.text().strip() or None,
        }


class BatchPurchaseDialog(QDialog):
    """Диалог пакетного ввода: дата+магазин один раз, дальше — строки."""

    def __init__(
        self, parent=None, *, prefill: Optional[Dict[str, Any]] = None
    ):
        super().__init__(parent)
        self.setWindowTitle('Пакетный ввод покупок')
        self.resize(760, 480)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        today = date.today()
        self.date_edit.setDate(QDate(today.year, today.month, today.day))
        # Дату всегда предлагаем сегодняшнюю, даже если prefill пришёл из
        # старого чека ("Повторить последний чек…") — это про "купить то
        # же самое сегодня", а не про правку истории задним числом.

        self.store_combo = QComboBox()
        setup_searchable_combo(
            self.store_combo, placeholder='Начни печатать магазин…'
        )
        self._reload_stores()
        if prefill and prefill.get('store_id') is not None:
            set_combo_by_data(self.store_combo, prefill['store_id'])

        header = QFormLayout()
        header.addRow('Дата:', self.date_edit)
        header.addRow('Магазин:', self.store_combo)

        self._rows: List[BatchRowWidget] = []
        self.rows_layout = QVBoxLayout()
        self.rows_layout.addStretch(1)

        rows_container = QWidget()
        rows_container.setLayout(self.rows_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(rows_container)

        btn_add_row = QPushButton('+ Строка')
        btn_quick_add_product = QPushButton('+ Новый продукт…')
        btn_add_row.clicked.connect(self.add_row)
        btn_quick_add_product.clicked.connect(self.quick_add_product)

        controls = QHBoxLayout()
        controls.addWidget(btn_add_row)
        controls.addWidget(btn_quick_add_product)
        controls.addStretch(1)

        buttons = QDialogButtonBox()
        buttons.addButton(QDialogButtonBox.StandardButton.Ok)
        buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._on_ok)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(header)
        layout.addLayout(controls)
        layout.addWidget(scroll, 1)
        layout.addWidget(buttons)
        self.setLayout(layout)

        prefill_rows = (prefill or {}).get('rows') or []
        if prefill_rows:
            # Строки прошлого чека — стартовая точка для правки, а не
            # финальные значения: цены могли измениться, количество
            # можно поправить перед сохранением.
            for row_data in prefill_rows:
                self.add_row(prefill_row=row_data)
        else:
            # Начинаем сразу с двух строк — партия из одного товара
            # заводится через обычный PurchaseDialog, сюда обычно идут
            # ради нескольких позиций разом.
            self.add_row()
            self.add_row()

        self._store_id: Optional[int] = None
        self._purchase_date: Optional[date] = None
        self._rows_data: List[Dict[str, Any]] = []

    def _reload_stores(self) -> None:
        current = self.store_combo.currentData()
        self.store_combo.clear()
        self.store_combo.addItem('— выбери магазин —', None)
        for s in get_cached(
            'stores', lambda: list_items_safe(store_crud, limit=5000)
        ):
            self.store_combo.addItem(s.name, s.id)
        if current is not None:
            set_combo_by_data(self.store_combo, current)

    def add_row(self, *, prefill_row: Optional[Dict[str, Any]] = None) -> None:
        """Добавляет строку партии, опционально предзаполненную.

        prefill_row — ключевой параметр (а не позиционный) специально:
        add_row подключён напрямую к btn_add_row.clicked, а PyQt при
        вызове слота из сигнала clicked(bool) может подставить checked
        как первый позиционный аргумент. Через keyword-only параметр
        такая путаница исключена в принципе, а не "случайно работает"
        благодаря тому, что кнопка не checkable.
        """
        if prefill_row:
            row = BatchRowWidget(
                self,
                product_id=prefill_row.get('product_id'),
                quantity=prefill_row.get('quantity'),
                price=prefill_row.get('price'),
            )
        else:
            row = BatchRowWidget(self)
        row.remove_requested.connect(self._remove_row)
        self._rows.append(row)
        # Вставляем перед addStretch(1), а не в конец — иначе новая
        # строка окажется НИЖЕ растяжки и визуально уедет вниз списка.
        self.rows_layout.insertWidget(self.rows_layout.count() - 1, row)

    def _remove_row(self, row: BatchRowWidget) -> None:
        """Убирает строку, но не даёт остаться совсем без единой.

        Партия из нуля строк не имеет смысла — проще не пускать
        пользователя в это состояние, чем потом отдельно обрабатывать
        пустой self._rows в _on_ok().
        """
        if len(self._rows) <= 1:
            return
        self._rows.remove(row)
        self.rows_layout.removeWidget(row)
        row.setParent(None)
        row.deleteLater()

    def quick_add_product(self) -> None:
        """Создаёт продукт прямо из партии, без похода в 'Данные…'.

        Переиспользует ProductDialog — второй диалог создания продукта
        с нуля тут не нужен, он бы только разъезжался с оригиналом при
        следующих правках валидации.
        """
        dlg = ProductDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        name, category_id, unit_id = dlg.values()
        try:
            product = create_item(
                product_crud,
                Product(name=name, category_id=category_id, unit_id=unit_id),
            )
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', str(e))
            return

        invalidate('products')
        for row in self._rows:
            row.reload_products()

        # Сразу подставляем новый продукт в последнюю строку — обычно
        # именно ради неё продукт и создавали.
        if self._rows:
            set_combo_by_data(self._rows[-1].product_combo, product.id)

    def _on_ok(self) -> None:
        store_id = self.store_combo.currentData()
        if store_id is None:
            QMessageBox.warning(self, 'Проверка', 'Выбери магазин.')
            return

        rows_data = []
        for row in self._rows:
            values = row.values()
            if values is not None:
                rows_data.append(values)

        if not rows_data:
            QMessageBox.information(
                self,
                'Ок',
                'Добавь хотя бы одну строку с выбранным продуктом.',
            )
            return

        self._store_id = int(store_id)
        self._purchase_date = self.date_edit.date().toPyDate()
        self._rows_data = rows_data
        self.accept()

    def values(self) -> Dict[str, Any]:
        """Данные для create_purchases_batch().
        Доступны только после accept().
        """
        return {
            'store_id': self._store_id,
            'purchase_date': self._purchase_date,
            'rows': self._rows_data,
        }
