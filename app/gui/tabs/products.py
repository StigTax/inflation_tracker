from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, cast

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)

from app.crud import category_crud, product_crud, unit_crud
from app.gui.qt_helpers import setup_searchable_combo
from app.gui.tabs.common import BaseCrudTab, list_items_safe, set_combo_by_data
from app.models import Product
from app.service.delete_guards import product_has_no_purchases


class ProductDialog(QDialog):
    """Диалог создания/редактирования продукта."""

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

        self.name_edit = QLineEdit(name)
        self.category_combo = QComboBox()
        self.unit_combo = QComboBox()

        setup_searchable_combo(
            self.category_combo,
            placeholder='Начни печатать категорию…'
        )
        setup_searchable_combo(
            self.unit_combo,
            placeholder='Начни печатать единицу…'
        )

        self.category_combo.addItem('— без категории —', None)
        for c in list_items_safe(category_crud, limit=5000):
            self.category_combo.addItem(c.name, c.id)

        self.unit_combo.addItem('— выбери единицу —', None)
        for u in list_items_safe(unit_crud, limit=5000):
            self.unit_combo.addItem(f'{u.measure_type} ({u.unit})', u.id)

        set_combo_by_data(self.category_combo, category_id)
        set_combo_by_data(self.unit_combo, unit_id)

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

    def values(self) -> Tuple[str, Optional[int], int]:
        """Возвращает значения формы."""
        name = self.name_edit.text().strip()
        category_id = cast(Optional[int], self.category_combo.currentData())
        unit_id = cast(int, self.unit_combo.currentData())
        return name, category_id, unit_id


class ProductsTab(BaseCrudTab):
    """CRUD-вкладка для продуктов."""

    entity_caption = 'Продукт'
    entity_accusative = 'продукт'

    crud = product_crud
    columns = [
        ('name', 'Название'),
        ('category', 'Категория'),
        ('measure_type', 'Тип'),
        ('unit', 'Ед.'),
    ]
    column_widths = {
        'name': 320,
        'category': 220,
        'measure_type': 120,
        'unit': 70,
    }
    stretch_column = 'name'
    enable_filter_bar = True
    search_placeholder = 'Поиск: продукт…'
    sort_options = [
        ('По названию: А→Я', ('name', 'asc')),
        ('По названию: Я→А', ('name', 'desc')),
        ('По категории: А→Я', ('category', 'asc')),
        ('По категории: Я→А', ('category', 'desc')),
    ]

    list_limit = 5000
    delete_guards = [product_has_no_purchases]

    enable_text_filter = True
    filter_placeholder = 'Фильтр по продуктам (название/категория/ед.)…'

    def get_order_by(self):
        return Product.name

    def pre_add_check(self) -> Optional[str]:
        if not list_items_safe(unit_crud, limit=1):
            return 'Сначала создай хотя бы одну единицу измерения.'
        return None

    def items_to_rows(self, items: List[Any]) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for p in cast(List[Product], items):
            rows.append(
                {
                    'id': p.id,
                    'name': p.name,
                    'category': p.category.name if p.category else '—',
                    'measure_type': p.unit.measure_type if p.unit else '—',
                    'unit': p.unit.unit if p.unit else '—',
                    'category_id': p.category_id,
                    'unit_id': p.unit_id,
                }
            )
        return rows

    def make_add_dialog(self) -> QDialog:
        return ProductDialog(self)

    def make_edit_dialog(self, row: Dict[str, Any]) -> QDialog:
        return ProductDialog(
            self,
            name=str(row.get('name') or ''),
            category_id=cast(Optional[int], row.get('category_id')),
            unit_id=cast(Optional[int], row.get('unit_id')),
        )

    def build_create_obj(self, dlg: QDialog) -> Any:
        d = cast(ProductDialog, dlg)
        name, category_id, unit_id = d.values()
        return Product(name=name, category_id=category_id, unit_id=unit_id)

    def build_update_fields(self, dlg: QDialog) -> Dict[str, Any]:
        d = cast(ProductDialog, dlg)
        name, category_id, unit_id = d.values()
        return {
            'name': name,
            'category_id': category_id,
            'unit_id': unit_id,
        }

    def _build_filter_bar(self, layout) -> None:
        super()._build_filter_bar(layout)

        self.filter_category_combo = QComboBox()
        setup_searchable_combo(
            self.filter_category_combo, placeholder='Категория…'
        )
        self.filter_category_combo.addItem('— все категории —', None)
        for c in list_items_safe(category_crud, limit=5000):
            self.filter_category_combo.addItem(c.name, c.name)

        self.filter_measure_type_combo = QComboBox()
        self.filter_measure_type_combo.addItem('— все типы —', None)

        units = list_items_safe(unit_crud, limit=5000)
        measure_types = sorted(
            {u.measure_type for u in units if u.measure_type}
        )

        for mt in measure_types:
            self.filter_measure_type_combo.addItem(mt, mt)

        layout.addSpacing(10)
        layout.addWidget(QLabel('Категория:'))
        layout.addWidget(self.filter_category_combo)

        layout.addSpacing(10)
        layout.addWidget(QLabel('Тип:'))
        layout.addWidget(self.filter_measure_type_combo)

    def get_equals_filters(self) -> Dict[str, Optional[str]]:
        return {
            'category': self.filter_category_combo.currentData(),
            'measure_type': self.filter_measure_type_combo.currentData(),
        }

    def reset_extra_filters(self) -> None:
        self.filter_category_combo.setCurrentIndex(0)
        self.filter_measure_type_combo.setCurrentIndex(0)
        self.filter_unit_combo.setCurrentIndex(0)
