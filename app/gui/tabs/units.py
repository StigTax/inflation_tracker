from __future__ import annotations

from PyQt6.QtWidgets import (
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

from app.crud import unit_crud
from app.gui.table_model import DictTableModel
from app.models.product import Unit
from app.service.crud_service import (
    create_item,
    delete_item,
    list_items,
    update_item,
)
from app.service.delete_guards import unit_has_no_products
from app.validate.exceptions import ObjectInUseError


class UnitDialog(QDialog):
    def __init__(self, parent=None, *, measure_type: str = "", unit: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Единица измерения")

        self.measure_type_edit = QLineEdit(measure_type)
        self.unit_edit = QLineEdit(unit)

        form = QFormLayout()
        form.addRow("Тип (например: вес/объём/штуки):", self.measure_type_edit)
        form.addRow("Единица (например: кг/л/шт):", self.unit_edit)

        buttons = QDialogButtonBox()
        buttons.addButton(QDialogButtonBox.StandardButton.Ok)
        buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def values(self) -> tuple[str, str]:
        measure_type = self.measure_type_edit.text().strip()
        unit = self.unit_edit.text().strip()
        return measure_type, unit


class UnitsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.table = QTableView()
        self.model = DictTableModel(
            columns=[
                ('measure_type', 'Тип единицы измерения'),
                ('unit', 'Единица измерения'),
            ],
            rows=[],
        )
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(
            QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(
            QTableView.SelectionMode.SingleSelection
        )

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
        items = list_items(unit_crud, limit=500)
        self.model.set_rows([c.to_dict() for c in items])

    def _selected_row(self) -> dict | None:
        idx = self.table.currentIndex()
        if not idx.isValid():
            return None
        return self.model.row_dict(idx.row())

    def on_add(self) -> None:
        dlg = UnitDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        measure_type, unit = dlg.values()
        try:
            create_item(unit_crud, Unit(measure_type=measure_type, unit=unit))
            self.reload()
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', str(e))

    def on_edit(self) -> None:
        row = self._selected_row()
        if not row:
            QMessageBox.information(
                self, 'Ок', 'Выбери единицу измерения в таблице.')
            return

        dlg = UnitDialog(
            self,
            measure_type=row.get('measure_type', ''),
            unit=row.get('unit', ''),
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        measure_type, unit = dlg.values()
        try:
            update_item(
                unit_crud,
                row['id'],
                measure_type=measure_type,
                unit=unit
            )
            self.reload()
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', str(e))

    def on_delete(self) -> None:
        row = self._selected_row()
        if not row:
            QMessageBox.information(
                self, 'Ок', 'Выбери единицу измерения в таблице.')
            return

        label = (
            f'{row.get("measure_type", "")} / {row.get("unit", "")}'.strip(
                ' /'
            )
        )
        ok = QMessageBox.question(
            self,
            'Подтверждение',
            f'Удалить единицу измерения "{label}" (id={row["id"]})?',
        )
        if ok != QMessageBox.StandardButton.Yes:
            return

        try:
            delete_item(unit_crud, row['id'], guards=[unit_has_no_products])
            self.reload()
        except ObjectInUseError as e:
            QMessageBox.warning(self, 'Нельзя удалить', str(e))
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', str(e))
