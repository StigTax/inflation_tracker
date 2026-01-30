from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, cast

from PyQt6.QtCore import QSortFilterProxyModel, Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableView,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.gui.table_model import DictTableModel
from app.service.crud_service import (
    create_item,
    delete_item,
    list_items,
    update_item,
)
from app.validate.exceptions import ObjectInUseError


def set_combo_by_data(combo, data: Any) -> None:
    """Выставляет QComboBox на элемент с нужным itemData.

    Args:
        combo: Комбо-бокс.
        data: Значение itemData, которое нужно выбрать.
    """
    for i in range(combo.count()):
        if combo.itemData(i) == data:
            combo.setCurrentIndex(i)
            return


def list_items_safe(crud, *, limit: int = 2000):
    """Обёртка над list_items для GUI.

    Args:
        crud: CRUD-объект.
        limit: Лимит.

    Returns:
        list: Список объектов.
    """
    return list_items(crud, limit=limit)


class MultiFilterProxyModel(QSortFilterProxyModel):
    """Proxy-модель с несколькими фильтрами.

    - text: подстрочный поиск по всем колонкам (case-insensitive)
    - equals_filters: точное совпадение по заданным колонкам
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._text: str = ''
        self._equals_filters: dict[int, Optional[str]] = {}
        self.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.setFilterKeyColumn(-1)

    def set_text(self, text: str) -> None:
        self._text = (text or '').strip().lower()
        self.invalidateFilter()

    def set_equals_filter(self, column: int, value: Optional[str]) -> None:
        self._equals_filters[column] = (
            value.strip() if isinstance(value, str) else None
        )
        self.invalidateFilter()

    def clear_equals_filters(self) -> None:
        self._equals_filters.clear()
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent) -> bool:
        m = self.sourceModel()
        if m is None:
            return True

        col_count = m.columnCount()

        # equals filters
        for col, expected in self._equals_filters.items():
            if expected is None:
                continue
            if col < 0 or col >= col_count:
                continue
            idx = m.index(source_row, col, source_parent)
            actual = m.data(idx)
            if str(actual).strip().lower() != str(expected).strip().lower():
                return False

        # text filter (contains in any column)
        if self._text:
            for col in range(col_count):
                idx = m.index(source_row, col, source_parent)
                val = m.data(idx)
                if self._text in str(val).lower():
                    return True
            return False

        return True


class NameDescDialog(QDialog):
    """Диалог 'Название + Описание'.

    Используется для магазинов и категорий.
    """

    def __init__(
        self,
        parent=None,
        *,
        title: str,
        name: str = '',
        description: str = '',
        name_label: str = 'Название:',
        desc_label: str = 'Описание:',
    ):
        super().__init__(parent)
        self.setWindowTitle(title)

        self.name_edit = QLineEdit(name)
        self.desc_edit = QTextEdit(description)
        self.desc_edit.setFixedHeight(90)

        form = QFormLayout()
        form.addRow(name_label, self.name_edit)
        form.addRow(desc_label, self.desc_edit)

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
                self, 'Проверка', 'Название не может быть пустым.')
            return
        self.accept()

    def values(self) -> Tuple[str, Optional[str]]:
        """Возвращает значения формы.

        Returns:
            tuple[str, Optional[str]]: (name, description)
        """
        name = self.name_edit.text().strip()
        desc = self.desc_edit.toPlainText().strip()
        return name, (desc if desc else None)


class UnitDialog(QDialog):
    """Диалог единицы измерения."""

    def __init__(
        self,
        parent=None,
        *,
        measure_type: str = '',
        unit: str = '',
    ):
        super().__init__(parent)
        self.setWindowTitle('Единица измерения')

        self.measure_type_edit = QLineEdit(measure_type)
        self.unit_edit = QLineEdit(unit)

        form = QFormLayout()
        form.addRow('Тип (например: вес/объём/штуки):', self.measure_type_edit)
        form.addRow('Единица (например: кг/л/шт):', self.unit_edit)

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
        measure_type = self.measure_type_edit.text().strip()
        unit = self.unit_edit.text().strip()

        if not measure_type:
            QMessageBox.warning(
                self, 'Проверка', 'Тип единицы измерения обязателен.')
            return
        if not unit:
            QMessageBox.warning(
                self, 'Проверка', 'Единица измерения обязательна.')
            return

        self.accept()

    def values(self) -> Tuple[str, str]:
        """Возвращает значения формы."""
        measure_type = self.measure_type_edit.text().strip()
        unit = self.unit_edit.text().strip()
        return measure_type, unit


class BaseCrudTab(QWidget):
    """База для CRUD-вкладок со справочниками + лента фильтрации/сортировки."""

    entity_caption: str = 'Объект'
    entity_accusative: str = 'объект'

    crud = None
    columns: List[Tuple[str, str]] = []
    list_limit: int = 500
    delete_guards: Optional[List[Any]] = None

    # Включает ленту (как у покупок)
    enable_filter_bar: bool = False

    # Настройка поиска
    search_placeholder: str = 'Поиск…'

    # Сортировка: список (label, (column_key, direction))
    # direction: 'asc'|'desc'
    sort_options: List[Tuple[str, Tuple[str, str]]] = []

    def __init__(self, parent=None):
        super().__init__(parent)

        # --- table + model ---
        self.table = QTableView()
        self.model = DictTableModel(columns=self.columns, rows=[])

        self.proxy = MultiFilterProxyModel(self)
        self.proxy.setSourceModel(self.model)

        self.table.setModel(self.proxy)
        self.table.setSelectionBehavior(
            QTableView.SelectionBehavior.SelectRows
        )
        self.table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self._apply_column_widths()

        # --- CRUD buttons ---
        btn_add = QPushButton('Добавить')
        btn_edit = QPushButton('Редактировать')
        btn_del = QPushButton('Удалить')
        btn_refresh = QPushButton('Обновить')

        btn_add.clicked.connect(self.on_add)
        btn_edit.clicked.connect(self.on_edit)
        btn_del.clicked.connect(self.on_delete)
        btn_refresh.clicked.connect(self.reload)

        crud_row = QHBoxLayout()
        crud_row.addWidget(btn_add)
        crud_row.addWidget(btn_edit)
        crud_row.addWidget(btn_del)
        crud_row.addStretch(1)
        crud_row.addWidget(btn_refresh)

        # --- Filter / Sort bar (как у покупок) ---
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(self.search_placeholder)

        self.sort_combo = QComboBox()
        for label, data in self.sort_options:
            self.sort_combo.addItem(label, data)

        btn_apply = QPushButton('Применить')
        btn_reset = QPushButton('Сброс')

        btn_apply.clicked.connect(self.apply_filters)
        btn_reset.clicked.connect(self.on_reset_filters)

        filter_row = QHBoxLayout()
        self._build_filter_bar(filter_row)
        filter_row.addSpacing(10)
        filter_row.addWidget(QLabel('Сортировка:'))
        filter_row.addWidget(self.sort_combo)
        filter_row.addWidget(btn_apply)
        filter_row.addWidget(btn_reset)

        # Скрываем ленту там, где она не нужна
        for i in range(filter_row.count()):
            w = filter_row.itemAt(i).widget()
            if w is not None:
                w.setVisible(self.enable_filter_bar)

        # --- layout ---
        layout = QVBoxLayout()
        layout.addLayout(crud_row)
        layout.addLayout(filter_row)
        layout.addWidget(self.table)
        self.setLayout(layout)

        self.reload()

    # ====== hooks для вкладок ======

    def _build_filter_bar(self, layout: QHBoxLayout) -> None:
        """Собирает левую часть ленты фильтрации.

        По умолчанию — только текстовый поиск.
        В наследниках добавляй комбобоксы.
        """
        layout.addWidget(QLabel('Поиск:'))
        layout.addWidget(self.search_edit)

    def get_equals_filters(self) -> Dict[str, Optional[str]]:
        """Возвращает equals-фильтры: {column_key: value|None}."""
        return {}

    def reset_extra_filters(self) -> None:
        """Сброс дополнительных фильтров в наследниках."""
        return

    # ====== internal helpers ======

    def _col_index(self, key: str) -> Optional[int]:
        for idx, (k, _) in enumerate(self.columns):
            if k == key:
                return idx
        return None

    def _selected_row(self) -> Optional[Dict[str, Any]]:
        idx = self.table.currentIndex()
        if not idx.isValid():
            return None
        src = self.proxy.mapToSource(idx)
        return cast(Dict[str, Any], self.model.row_dict(src.row()))

    def _info_select_row(self) -> None:
        QMessageBox.information(
            self,
            'Ок',
            f'Выбери {self.entity_accusative} в таблице.'
        )

    def _apply_column_widths(self) -> None:
        """Применяет стартовые ширины колонок и режимы ресайза."""
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)

        widths = getattr(self, 'column_widths', {})
        stretch_key = getattr(self, 'stretch_column', None)

        for col_idx, (key, _) in enumerate(self.columns):
            if key in widths:
                self.table.setColumnWidth(col_idx, int(widths[key]))

        if stretch_key:
            for col_idx, (key, _) in enumerate(self.columns):
                if key == stretch_key:
                    header.setSectionResizeMode(
                        col_idx,
                        QHeaderView.ResizeMode.Stretch
                    )
                    break

    # ====== filtering/sorting ======

    def apply_filters(self) -> None:
        """Применяет фильтры + сортировку к proxy."""
        if not self.enable_filter_bar:
            return

        # text
        self.proxy.set_text(self.search_edit.text())

        # equals filters
        self.proxy.clear_equals_filters()
        for col_key, val in self.get_equals_filters().items():
            col_idx = self._col_index(col_key)
            if col_idx is None:
                continue
            self.proxy.set_equals_filter(col_idx, val)

        # sort
        data = self.sort_combo.currentData()
        if data:
            col_key, direction = data
            col_idx = self._col_index(col_key)
            if col_idx is not None:
                order = (
                    Qt.SortOrder.AscendingOrder
                    if direction == 'asc'
                    else Qt.SortOrder.DescendingOrder
                )
                self.proxy.sort(col_idx, order)

    def on_reset_filters(self) -> None:
        if not self.enable_filter_bar:
            return

        self.search_edit.setText('')
        if self.sort_combo.count():
            self.sort_combo.setCurrentIndex(0)

        self.reset_extra_filters()
        self.apply_filters()

    # ====== CRUD actions ======

    def reload(self) -> None:
        items = list_items(self.crud, limit=self.list_limit)
        self.model.set_rows(self.items_to_rows(items))
        self.apply_filters()

    def pre_add_check(self) -> Optional[str]:
        return None

    def items_to_rows(self, items: List[Any]) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for item in items:
            if hasattr(item, 'to_dict') and callable(item.to_dict):
                rows.append(item.to_dict())
            else:
                rows.append(dict(item.__dict__))
        return rows

    def make_add_dialog(self) -> QDialog:
        raise NotImplementedError

    def make_edit_dialog(self, row: Dict[str, Any]) -> QDialog:
        raise NotImplementedError

    def build_create_obj(self, dlg: QDialog) -> Any:
        raise NotImplementedError

    def build_update_fields(self, dlg: QDialog) -> Dict[str, Any]:
        raise NotImplementedError

    def delete_label(self, row: Dict[str, Any]) -> str:
        name = row.get('name')
        return str(name) if name else f'id={row.get("id")}'

    def on_add(self) -> None:
        msg = self.pre_add_check()
        if msg:
            QMessageBox.warning(self, 'Нельзя', msg)
            return

        dlg = self.make_add_dialog()
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        try:
            obj = self.build_create_obj(dlg)
            create_item(self.crud, obj)
            self.reload()
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', str(e))

    def on_edit(self) -> None:
        row = self._selected_row()
        if not row:
            self._info_select_row()
            return

        dlg = self.make_edit_dialog(row)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        try:
            fields = self.build_update_fields(dlg)
            update_item(self.crud, int(row['id']), **fields)
            self.reload()
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', str(e))

    def on_delete(self) -> None:
        row = self._selected_row()
        if not row:
            self._info_select_row()
            return

        label = self.delete_label(row)
        ok = QMessageBox.question(
            self,
            'Подтверждение',
            f'Удалить {self.entity_accusative}: "{label}" (id={row["id"]})?',
        )
        if ok != QMessageBox.StandardButton.Yes:
            return

        try:
            delete_item(
                self.crud,
                int(row['id']
            ), guards=list(self.delete_guards or []))
            self.reload()
        except ObjectInUseError as e:
            QMessageBox.warning(self, 'Нельзя удалить', str(e))
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', str(e))
