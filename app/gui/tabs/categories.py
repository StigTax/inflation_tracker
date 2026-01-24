'''Вкладка GUI для категорий.'''

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
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.crud import category_crud
from app.gui.table_model import DictTableModel
from app.models.category import Category
from app.service.crud_service import (
    create_item,
    delete_item,
    list_items,
    update_item,
)
from app.service.delete_guards import category_has_no_products
from app.validate.exceptions import ObjectInUseError


class CategoryDialog(QDialog):
    def __init__(
        self,
        parent=None,
        *,
        name: str = '',
        description: str = ''
    ):
        super().__init__(parent)
        self.setWindowTitle('Категория')

        self.name_edit = QLineEdit(name)
        self.desc_edit = QTextEdit(description)
        self.desc_edit.setFixedHeight(90)

        form = QFormLayout()
        form.addRow('Название:', self.name_edit)
        form.addRow('Описание:', self.desc_edit)

        buttons = QDialogButtonBox()
        buttons.addButton(QDialogButtonBox.StandardButton.Ok)
        buttons.addButton(QDialogButtonBox.StandardButton.Cancel)

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def values(self) -> tuple[str, str | None]:
        name = self.name_edit.text().strip()
        desc = self.desc_edit.toPlainText().strip()
        return name, (desc if desc else None)


class CategoriesTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.table = QTableView()
        self.model = DictTableModel(
            columns=[
                ('name', 'Название'),
                ('description', 'Описание'),
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
        items = list_items(category_crud, limit=500)
        self.model.set_rows([c.to_dict() for c in items])

    def _selected_row(self) -> dict | None:
        idx = self.table.currentIndex()
        if not idx.isValid():
            return None
        return self.model.row_dict(idx.row())

    def on_add(self) -> None:
        dlg = CategoryDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        name, desc = dlg.values()
        try:
            create_item(category_crud, Category(name=name, description=desc))
            self.reload()
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', str(e))

    def on_edit(self) -> None:
        row = self._selected_row()
        if not row:
            QMessageBox.information(self, 'Ок', 'Выбери категорию в таблице.')
            return

        dlg = CategoryDialog(self, name=row.get(
            'name', ''), description=row.get('description') or '')
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        name, desc = dlg.values()
        try:
            update_item(category_crud, row['id'], name=name, description=desc)
            self.reload()
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', str(e))

    def on_delete(self) -> None:
        row = self._selected_row()
        if not row:
            QMessageBox.information(self, 'Ок', 'Выбери категорию в таблице.')
            return

        ok = QMessageBox.question(
            self,
            'Подтверждение',
            f'Удалить категорию \"{row.get("name")}\" (id={row["id"]})?',
        )
        if ok != QMessageBox.StandardButton.Yes:
            return

        try:
            delete_item(category_crud, row['id'], guards=[
                        category_has_no_products])
            self.reload()
        except ObjectInUseError as e:
            QMessageBox.warning(self, 'Нельзя удалить', str(e))
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', str(e))
