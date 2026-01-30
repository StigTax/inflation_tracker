from __future__ import annotations

from typing import Any, Dict, cast

from PyQt6.QtWidgets import QDialog

from app.crud import category_crud
from app.gui.tabs.common import BaseCrudTab, NameDescDialog
from app.models import Category
from app.service.delete_guards import category_has_no_products


class CategoriesTab(BaseCrudTab):
    """CRUD-вкладка для категорий."""

    entity_caption = 'Категория'
    entity_accusative = 'категорию'

    crud = category_crud
    columns = [
        ('name', 'Название'),
        ('description', 'Описание'),
    ]
    column_widths = {
        'name': 300,
    }
    stretch_column = 'description'

    enable_filter_bar = True
    search_placeholder = 'Поиск: категория…'
    sort_options = [
        ('По названию: А→Я', ('name', 'asc')),
        ('По названию: Я→А', ('name', 'desc')),
    ]

    delete_guards = [category_has_no_products]

    def make_add_dialog(self) -> QDialog:
        return NameDescDialog(self, title='Категория')

    def make_edit_dialog(self, row: Dict[str, Any]) -> QDialog:
        return NameDescDialog(
            self,
            title='Категория',
            name=str(row.get('name') or ''),
            description=str(row.get('description') or ''),
        )

    def build_create_obj(self, dlg: QDialog) -> Any:
        d = cast(NameDescDialog, dlg)
        name, desc = d.values()
        return Category(name=name, description=desc)

    def build_update_fields(self, dlg: QDialog) -> Dict[str, Any]:
        d = cast(NameDescDialog, dlg)
        name, desc = d.values()
        return {
            'name': name,
            'description': desc,
        }
