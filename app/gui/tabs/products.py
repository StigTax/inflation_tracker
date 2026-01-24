from __future__ import annotations

from typing import Optional

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from app.crud import category_crud, product_crud, unit_crud
from app.gui.table_model import DictTableModel
from app.models import Product
from app.service.crud_service import (
    create_item,
    delete_item,
    list_items,
    update_item,
)
from app.service.delete_guards import product_has_no_purchases
from app.validate.exceptions import ObjectInUseError


def _set_combo_by_data(combo: QComboBox, data) -> None:
    for i in range(combo.count()):
        if combo.itemData(i) == data:
            combo.setCurrentIndex(i)
            return


class ProductDialog(QDialog):
    def __init__(
        self,
        parent=None,
        *,
        name: str = '',
        category_id: Optional[int] = None,
        unit_id: Optional[int] = None,
    ):
        super().__init__(parent)
        self.setWindowTitle('Продукт')

        # Поля
        self.name_edit = QLineEdit(name)
        self.category_combo = QComboBox()
        self.unit_combo = QComboBox()

        # Загружаем справочники
        categories = list_items(category_crud, limit=1000)
        units = list_items(unit_crud, limit=1000)

        # Категория: может быть None
        self.category_combo.addItem('— без категории —', None)
        for c in categories:
            self.category_combo.addItem(c.name, c.id)

        # Единица: обязана быть
        self.unit_combo.addItem('— выбери единицу —', None)
        for u in units:
            self.unit_combo.addItem(f'{u.measure_type} ({u.unit})', u.id)

        # Проставляем текущие значения (если редактирование)
        _set_combo_by_data(self.category_combo, category_id)
        _set_combo_by_data(self.unit_combo, unit_id)

        form = QFormLayout()
        form.addRow('Название:', self.name_edit)
        form.addRow('Категория:', self.category_combo)
        form.addRow('Единица:', self.unit_combo)

        buttons = QDialogButtonBox()
        buttons.addButton(QDialogButtonBox.StandardButton.Ok)
        buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._on_ok)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def _on_ok(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(
                self,
                'Проверка',
                'Название не может быть пустым.'
            )
            return

        if self.unit_combo.currentData() is None:
            QMessageBox.warning(
                self,
                'Проверка',
                'Единица измерения обязательна.'
            )
            return

        self.accept()

    def values(self) -> tuple[str, int | None, int]:
        name = self.name_edit.text().strip()
        category_id = self.category_combo.currentData()
        unit_id = self.unit_combo.currentData()
        return name, category_id, unit_id


class ProductsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.table = QTableView()
        self.model = DictTableModel(
            columns=[
                ('name', 'Название'),
                ('category', 'Категория'),
                ('measure_type', 'Тип'),
                ('unit', 'Ед.'),
            ],
            rows=[],
        )
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(
            QTableView.SelectionBehavior.SelectRows
        )
        self.table.setSelectionMode(QTableView.SelectionMode.SingleSelection)

        btn_add = QPushButton('Добавить')
        btn_edit = QPushButton('Редактировать')
        btn_del = QPushButton('Удалить')
        btn_refresh = QPushButton('Обновить')

        btn_add.clicked.connect(self.on_add)
        btn_edit.clicked.connect(self.on_edit)
        btn_del.clicked.connect(self.on_delete)
        btn_refresh.clicked.connect(self.reload)

        top = QHBoxLayout()
        top.addWidget(btn_add)
        top.addWidget(btn_edit)
        top.addWidget(btn_del)
        top.addStretch(1)
        top.addWidget(btn_refresh)

        layout = QVBoxLayout()
        layout.addLayout(top)
        layout.addWidget(self.table)
        self.setLayout(layout)

        self.reload()

    def reload(self) -> None:
        items = list_items(product_crud, limit=1000, order_by=Product.name)
        rows = []
        for p in items:
            rows.append({
                'id': p.id,
                'name': p.name,
                'category': p.category.name if p.category else '—',
                'measure_type': p.unit.measure_type if p.unit else '—',
                'unit': p.unit.unit if p.unit else '—',

                'category_id': p.category_id,
                'unit_id': p.unit_id,
            })

        self.model.set_rows(rows)

    def _selected_row(self) -> dict | None:
        idx = self.table.currentIndex()
        if not idx.isValid():
            return None
        return self.model.row_dict(idx.row())

    def on_add(self) -> None:
        # Если нет units — смысла нет: unit_id обязателен
        units = list_items(unit_crud, limit=1)
        if not units:
            QMessageBox.warning(
                self,
                'Нельзя',
                'Сначала создай хотя бы одну единицу измерения.'
            )
            return

        dlg = ProductDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        name, category_id, unit_id = dlg.values()
        try:
            create_item(
                product_crud,
                Product(name=name, category_id=category_id, unit_id=unit_id),
            )
            self.reload()
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', str(e))

    def on_edit(self) -> None:
        row = self._selected_row()
        if not row:
            QMessageBox.information(self, 'Ок', 'Выбери продукт в таблице.')
            return

        dlg = ProductDialog(
            self,
            name=row.get('name', ''),
            category_id=row.get('category_id'),
            unit_id=row.get('unit_id'),
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        name, category_id, unit_id = dlg.values()
        try:
            update_item(
                product_crud,
                row['id'],
                name=name,
                category_id=category_id,
                unit_id=unit_id,
            )
            self.reload()
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', str(e))

    def on_delete(self) -> None:
        row = self._selected_row()
        if not row:
            QMessageBox.information(
                self,
                'Ок',
                'Выбери продукт в таблице.'
            )
            return

        ok = QMessageBox.question(
            self,
            'Подтверждение',
            f'Удалить продукт "{row.get("name")}" (id={row["id"]})?',
        )
        if ok != QMessageBox.StandardButton.Yes:
            return

        try:
            delete_item(
                product_crud,
                row['id'],
                guards=[product_has_no_purchases]
            )
            self.reload()
        except ObjectInUseError as e:
            QMessageBox.warning(self, 'Нельзя удалить', str(e))
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', str(e))
