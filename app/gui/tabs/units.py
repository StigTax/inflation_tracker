from __future__ import annotations

from typing import Any, Dict, cast

from PyQt6.QtWidgets import QDialog

from app.crud import unit_crud
from app.gui.tabs.common import BaseCrudTab, UnitDialog
from app.models import Unit
from app.service.delete_guards import unit_has_no_products


class UnitsTab(BaseCrudTab):
    """CRUD-вкладка для единиц измерения."""

    entity_caption = 'Единица измерения'
    entity_accusative = 'единицу измерения'

    crud = unit_crud
    columns = [
        ('measure_type', 'Тип единицы измерения'),
        ('unit', 'Единица измерения'),
    ]
    column_widths = {
        'measure_type': 180,
        'unit': 100,
    }

    delete_guards = [unit_has_no_products]

    def make_add_dialog(self) -> QDialog:
        return UnitDialog(self)

    def make_edit_dialog(self, row: Dict[str, Any]) -> QDialog:
        return UnitDialog(
            self,
            measure_type=str(row.get('measure_type') or ''),
            unit=str(row.get('unit') or ''),
        )

    def build_create_obj(self, dlg: QDialog) -> Any:
        d = cast(UnitDialog, dlg)
        measure_type, unit = d.values()
        return Unit(measure_type=measure_type, unit=unit)

    def build_update_fields(self, dlg: QDialog) -> Dict[str, Any]:
        d = cast(UnitDialog, dlg)
        measure_type, unit = d.values()
        return {
            'measure_type': measure_type,
            'unit': unit,
        }

    def delete_label(self, row: Dict[str, Any]) -> str:
        measure_type = str(row.get('measure_type') or '')
        unit = str(row.get('unit') or '')
        label = f'{measure_type} / {unit}'.strip(' /')
        return label or super().delete_label(row)
