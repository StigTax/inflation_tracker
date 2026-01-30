from __future__ import annotations

from typing import Any, Dict, cast

from PyQt6.QtWidgets import QDialog

from app.crud import store_crud
from app.gui.tabs.common import BaseCrudTab, NameDescDialog
from app.models import Store
from app.service.delete_guards import store_has_no_purchases


class StoresTab(BaseCrudTab):
    """CRUD-вкладка для магазинов.

    Дополнительно включает строку фильтрации по тексту, потому что магазинов
    со временем становится много, а мышка — не бесконечна.
    """

    entity_caption = 'Магазин'
    entity_accusative = 'магазин'

    crud = store_crud
    columns = [
        ('name', 'Название'),
        ('description', 'Описание'),
    ]
    column_widths = {
        'name': 300,
    }
    stretch_column = 'description'
    enable_filter_bar = True
    search_placeholder = 'Поиск: магазин…'
    sort_options = [
        ('По названию: А→Я', ('name', 'asc')),
        ('По названию: Я→А', ('name', 'desc')),
    ]

    delete_guards = [store_has_no_purchases]

    enable_text_filter = True
    filter_placeholder = 'Фильтр по названию/описанию…'

    def make_add_dialog(self) -> QDialog:
        return NameDescDialog(self, title='Магазин')

    def make_edit_dialog(self, row: Dict[str, Any]) -> QDialog:
        return NameDescDialog(
            self,
            title='Магазин',
            name=str(row.get('name') or ''),
            description=str(row.get('description') or ''),
        )

    def build_create_obj(self, dlg: QDialog) -> Any:
        d = cast(NameDescDialog, dlg)
        name, desc = d.values()
        return Store(name=name, description=desc)

    def build_update_fields(self, dlg: QDialog) -> Dict[str, Any]:
        d = cast(NameDescDialog, dlg)
        name, desc = d.values()
        return {
            'name': name,
            'description': desc,
        }
