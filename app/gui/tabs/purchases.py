"""Вкладка GUI для покупок."""

from __future__ import annotations

from datetime import date
from typing import Optional, cast

from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableView,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.crud import product_crud, store_crud
from app.gui.table_model import DictTableModel
from app.models import Purchase
from app.service.purchases import (
    create_purchase,
    delete_purchase,
    get_purchase_by_product,
    get_purchase_by_store,
    list_purchases,
    update_purchase,
)


def _set_combo_by_data(combo: QComboBox, data) -> None:
    for i in range(combo.count()):
        if combo.itemData(i) == data:
            combo.setCurrentIndex(i)
            return


def list_items_safe(crud, limit: int = 2000):
    from app.service.crud_service import list_items
    return list_items(crud, limit=limit)


class PurchaseDialog(QDialog):
    def __init__(
        self,
        parent=None,
        *,
        purchase_date: Optional[date] = None,
        product_id: Optional[int]  = None,
        store_id: Optional[int]  = None,
        quantity: Optional[float]  = None,
        total_price: Optional[float] = None,
        comment: Optional[str] = None,
        is_promo: bool = False,
        promo_type: Optional[str] = None,
        regular_unit_price: Optional[float] = None,
    ):
        super().__init__(parent)
        self.setWindowTitle('Покупка')

        products = list_items_safe(product_crud)
        stores = list_items_safe(store_crud)

        self.product_combo = QComboBox()
        self.store_combo = QComboBox()

        self.product_combo.addItem('— выбери продукт —', None)
        for p in products:
            label = (
                f'{p.name} ({p.unit.measure_type} {p.unit.unit}) (id={p.id})'
            )
            self.product_combo.addItem(label, p.id)

        self.store_combo.addItem('— выбери магазин —', None)
        for s in stores:
            self.store_combo.addItem(f'{s.name} (id={s.id})', s.id)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        d = purchase_date or date.today()
        self.date_edit.setDate(QDate(d.year, d.month, d.day))

        self.quantity_spin = QDoubleSpinBox()
        self.quantity_spin.setDecimals(3)
        self.quantity_spin.setRange(0.001, 1_000_000)
        self.quantity_spin.setValue(float(quantity) if quantity else 1.0)

        self.price_spin = QDoubleSpinBox()
        self.price_spin.setDecimals(2)
        self.price_spin.setRange(0.01, 1_000_000_000)
        self.price_spin.setValue(float(total_price) if total_price else 0.01)

        self.unit_price_label = QLabel('Цена за единицу: —')
        self.quantity_spin.valueChanged.connect(self._update_unit_price)
        self.price_spin.valueChanged.connect(self._update_unit_price)
        self._update_unit_price()

        self.is_promo_check = QCheckBox('Акция')
        self.is_promo_check.setChecked(bool(is_promo))
        self.is_promo_check.stateChanged.connect(self._toggle_promo_fields)

        self.promo_type_combo = QComboBox()
        self.promo_type_combo.addItem('— тип акции —', None)
        for t in [
            'discount',
            'multi_buy',
            'loyalty',
            'clearance',
            'coupon',
            'cashback'
        ]:
            self.promo_type_combo.addItem(t, t)

        self.regular_price_spin = QDoubleSpinBox()
        self.regular_price_spin.setDecimals(2)
        self.regular_price_spin.setRange(0.01, 1_000_000_000)
        self.regular_price_spin.setValue(
            float(regular_unit_price) if regular_unit_price else 0.01)

        self.comment_edit = QTextEdit()
        self.comment_edit.setFixedHeight(80)
        self.comment_edit.setPlainText(comment or '')

        _set_combo_by_data(self.product_combo, product_id)
        _set_combo_by_data(self.store_combo, store_id)
        _set_combo_by_data(self.promo_type_combo, promo_type)

        self._toggle_promo_fields()

        form = QFormLayout()
        form.addRow('Дата:', self.date_edit)
        form.addRow('Продукт:', self.product_combo)
        form.addRow('Магазин:', self.store_combo)
        form.addRow('Количество:', self.quantity_spin)
        form.addRow('Сумма:', self.price_spin)
        form.addRow('', self.unit_price_label)
        form.addRow('', self.is_promo_check)
        form.addRow('Тип акции:', self.promo_type_combo)
        form.addRow('Обычная цена/ед.:', self.regular_price_spin)
        form.addRow('Комментарий:', self.comment_edit)

        buttons = QDialogButtonBox()
        buttons.addButton(QDialogButtonBox.StandardButton.Ok)
        buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._on_ok)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def _update_unit_price(self) -> None:
        q = self.quantity_spin.value()
        p = self.price_spin.value()
        if q > 0:
            self.unit_price_label.setText(f'Цена за единицу: {p / q:.2f}')
        else:
            self.unit_price_label.setText('Цена за единицу: —')

    def _toggle_promo_fields(self) -> None:
        enabled = self.is_promo_check.isChecked()
        self.promo_type_combo.setEnabled(enabled)
        self.regular_price_spin.setEnabled(enabled)

    def _on_ok(self) -> None:
        if self.product_combo.currentData() is None:
            QMessageBox.warning(self, 'Проверка', 'Выбери продукт.')
            return
        if self.store_combo.currentData() is None:
            QMessageBox.warning(
                self,
                'Проверка',
                'Выбери магазин.'
            )
            return
        self.accept()

    def values(self) -> dict:
        comment = self.comment_edit.toPlainText().strip() or None
        is_promo = self.is_promo_check.isChecked()
        promo_type = self.promo_type_combo.currentData() if is_promo else None
        regular_unit_price = (
            self.regular_price_spin.value() if is_promo else None
        )
        return {
            'purchase_date': self.date_edit.date().toPyDate(),
            'product_id': int(self.product_combo.currentData()),
            'store_id': int(self.store_combo.currentData()),
            'quantity': float(self.quantity_spin.value()),
            'total_price': float(self.price_spin.value()),
            'comment': comment,
            'is_promo': is_promo,
            'promo_type': promo_type,
            'regular_unit_price': float(
                regular_unit_price
            ) if regular_unit_price is not None else None,
        }


class PurchasesTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # --- таблица ---
        self.table = QTableView()
        self.model = DictTableModel(
            columns=[
                ('purchase_date', 'Дата'),
                ('product', 'Продукт'),
                ('category', 'Категория'),
                ('store', 'Магазин'),
                ('quantity', 'Кол-во'),
                ('total_price', 'Сумма'),
                ('unit_price', 'Цена/ед.'),
                ('unit', 'Ед.'),
                ('is_promo', 'Акция'),
                ('comment', 'Комментарий'),
            ],
            rows=[],
        )
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(
            QTableView.SelectionBehavior.SelectRows
        )
        self.table.setSelectionMode(QTableView.SelectionMode.SingleSelection)

        # --- кнопки CRUD ---
        btn_add = QPushButton('Добавить')
        btn_edit = QPushButton('Редактировать')
        btn_del = QPushButton('Удалить')

        btn_add.clicked.connect(self.on_add)
        btn_edit.clicked.connect(self.on_edit)
        btn_del.clicked.connect(self.on_delete)

        crud_row = QHBoxLayout()
        crud_row.addWidget(btn_add)
        crud_row.addWidget(btn_edit)
        crud_row.addWidget(btn_del)
        crud_row.addStretch(1)

        # --- фильтры ---
        self.filter_product_combo = QComboBox()
        self.filter_store_combo = QComboBox()

        self.filter_date_check = QCheckBox('Фильтр по датам')
        self.filter_from = QDateEdit()
        self.filter_to = QDateEdit()

        self.filter_from.setCalendarPopup(True)
        self.filter_to.setCalendarPopup(True)

        today = date.today()
        self.filter_from.setDate(QDate(today.year, today.month, 1))
        self.filter_to.setDate(QDate(today.year, today.month, today.day))

        self.filter_from.setEnabled(False)
        self.filter_to.setEnabled(False)
        self.filter_date_check.stateChanged.connect(self._toggle_date_filters)

        self.sort_combo = QComboBox()
        self.sort_combo.addItem('Сначала новые', 'desc')
        self.sort_combo.addItem('Сначала старые', 'asc')

        btn_apply = QPushButton('Применить')
        btn_reset = QPushButton('Сброс')

        btn_apply.clicked.connect(self.reload)
        btn_reset.clicked.connect(self.on_reset_filters)

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel('Продукт:'))
        filter_row.addWidget(self.filter_product_combo)
        filter_row.addWidget(QLabel('Магазин:'))
        filter_row.addWidget(self.filter_store_combo)
        filter_row.addSpacing(10)
        filter_row.addWidget(self.filter_date_check)
        filter_row.addWidget(QLabel('с'))
        filter_row.addWidget(self.filter_from)
        filter_row.addWidget(QLabel('по'))
        filter_row.addWidget(self.filter_to)
        filter_row.addSpacing(10)
        filter_row.addWidget(QLabel('Сортировка:'))
        filter_row.addWidget(self.sort_combo)
        filter_row.addWidget(btn_apply)
        filter_row.addWidget(btn_reset)

        # --- низ: счётчик ---
        self.count_label = QLabel('Показано покупок: 0')
        bottom = QHBoxLayout()
        bottom.addWidget(self.count_label)
        bottom.addStretch(1)

        # --- layout ---
        layout = QVBoxLayout()
        layout.addLayout(crud_row)
        layout.addLayout(filter_row)
        layout.addWidget(self.table)
        layout.addLayout(bottom)
        self.setLayout(layout)

        self._load_filter_data()
        self.reload()

    def _toggle_date_filters(self) -> None:
        enabled = self.filter_date_check.isChecked()
        self.filter_from.setEnabled(enabled)
        self.filter_to.setEnabled(enabled)

    def _load_filter_data(self) -> None:
        # Продукты
        self.filter_product_combo.clear()
        self.filter_product_combo.addItem('— все продукты —', None)
        for p in list_items_safe(product_crud, limit=5000):
            self.filter_product_combo.addItem(p.name, p.id)

        # Магазины
        self.filter_store_combo.clear()
        self.filter_store_combo.addItem('— все магазины —', None)
        for s in list_items_safe(store_crud, limit=5000):
            self.filter_store_combo.addItem(s.name, s.id)

    def _selected_row(self) -> dict | None:
        idx = self.table.currentIndex()
        if not idx.isValid():
            return None
        return self.model.row_dict(idx.row())

    def _current_filters(self) -> dict:
        product_id = self.filter_product_combo.currentData()
        store_id = self.filter_store_combo.currentData()

        from_date = None
        to_date = None
        if self.filter_date_check.isChecked():
            from_date = self.filter_from.date().toPyDate()
            to_date = self.filter_to.date().toPyDate()

        sort_dir = self.sort_combo.currentData()  # 'asc' или 'desc'
        return {
            'product_id': product_id,
            'store_id': store_id,
            'from_date': from_date,
            'to_date': to_date,
            'sort_dir': sort_dir,
        }

    def on_reset_filters(self) -> None:
        _set_combo_by_data(self.filter_product_combo, None)
        _set_combo_by_data(self.filter_store_combo, None)

        self.filter_date_check.setChecked(False)

        today = date.today()
        self.filter_from.setDate(QDate(today.year, today.month, 1))
        self.filter_to.setDate(QDate(today.year, today.month, today.day))

        self.sort_combo.setCurrentIndex(0)  # новые
        self.reload()

    def reload(self) -> None:
        f = self._current_filters()
        sort_desc = f['sort_dir'] == 'desc'

        items: list[Purchase]

        if f['product_id'] is not None:
            items = get_purchase_by_product(
                product_id=f['product_id'],
                from_date=f['from_date'],
                to_date=f['to_date'],
            )
            if f['store_id'] is not None:
                items = [p for p in items if p.store_id == f['store_id']]

        elif f['store_id'] is not None:
            items = get_purchase_by_store(store_id=f['store_id'])

            if f['from_date'] is not None:
                items = [p for p in items if p.purchase_date >= f['from_date']]
            if f['to_date'] is not None:
                items = [p for p in items if p.purchase_date <= f['to_date']]

        else:
            order_by = Purchase.purchase_date.desc(
            ) if sort_desc else Purchase.purchase_date.asc()
            items = list_purchases(limit=2000, order_by=order_by)

            if f['from_date'] is not None:
                items = [p for p in items if p.purchase_date >= f['from_date']]
            if f['to_date'] is not None:
                items = [p for p in items if p.purchase_date <= f['to_date']]

        items = sorted(
            items,
            key=lambda p: cast(date, p.purchase_date),
            reverse=sort_desc)

        rows = [p.to_dict() for p in items]
        self.model.set_rows(rows)
        self.count_label.setText(f'Показано покупок: {len(rows)}')

    def on_add(self) -> None:
        if not list_items_safe(product_crud, limit=1):
            QMessageBox.warning(
                self, 'Нельзя', 'Сначала создай хотя бы один продукт.')
            return
        if not list_items_safe(store_crud, limit=1):
            QMessageBox.warning(
                self, 'Нельзя', 'Сначала создай хотя бы один магазин.')
            return

        dlg = PurchaseDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        v = dlg.values()
        try:
            create_purchase(
                store_id=v['store_id'],
                product_id=v['product_id'],
                quantity=v['quantity'],
                price=v['total_price'],
                purchase_date=v['purchase_date'],
                comment=v['comment'],
                is_promo=v['is_promo'],
                promo_type=v['promo_type'],
                regular_unit_price=v['regular_unit_price'],
            )
            self.reload()
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', str(e))

    def on_edit(self) -> None:
        row = self._selected_row()
        if not row:
            QMessageBox.information(self, 'Ок', 'Выбери покупку в таблице.')
            return

        dlg = PurchaseDialog(
            self,
            purchase_date=row.get('purchase_date'),
            product_id=row.get('product_id'),
            store_id=row.get('store_id'),
            quantity=row.get('quantity'),
            total_price=row.get('total_price'),
            comment=row.get('comment'),
            is_promo=bool(row.get('is_promo')),
            promo_type=row.get('promo_type'),
            regular_unit_price=row.get('regular_unit_price'),
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        v = dlg.values()
        try:
            update_purchase(
                purchase_id=row['id'],
                store_id=v['store_id'],
                product_id=v['product_id'],
                total_price=v['total_price'],
                quantity=v['quantity'],
                purchase_date=v['purchase_date'],
                comment=v['comment'],
                is_promo=v['is_promo'],
                promo_type=v['promo_type'],
                regular_unit_price=v['regular_unit_price'],
            )
            self.reload()
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', str(e))

    def on_delete(self) -> None:
        row = self._selected_row()
        if not row:
            QMessageBox.information(self, 'Ок', 'Выбери покупку в таблице.')
            return

        label = (
            f'{row.get("purchase_date")} — {row.get("product")} —'
            f'{row.get("store")}'
        )
        ok = QMessageBox.question(
            self,
            'Подтверждение',
            f'Удалить покупку: {label} (id={row["id"]})?',
        )
        if ok != QMessageBox.StandardButton.Yes:
            return

        try:
            delete_purchase(row['id'])
            self.reload()
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', str(e))
