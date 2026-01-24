"""Табличная модель для GUI."""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt


class DictTableModel(QAbstractTableModel):
    def __init__(
        self,
        columns: list[tuple[str, str]],
        rows: Optional[list[dict]] = None,
    ):
        super().__init__()
        self._columns = columns
        self._rows: list[dict] = rows or []

    def set_rows(
        self,
        rows: list[dict]
    ) -> None:
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()

    def rowCount(
        self,
        parent: QModelIndex = QModelIndex()
    ) -> int:
        return len(self._rows)

    def columnCount(
        self,
        parent: QModelIndex = QModelIndex()
    ) -> int:
        return len(self._columns)

    def data(
        self,
        index: QModelIndex,
        role: int = Qt.ItemDataRole.DisplayRole
    ):
        if not index.isValid():
            return None
        if role not in (
            Qt.ItemDataRole.DisplayRole,
            Qt.ItemDataRole.EditRole
        ):
            return None

        row = self._rows[index.row()]
        key = self._columns[index.column()][0]
        val = row.get(key)
        return '' if val is None else str(val)

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole
    ):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return self._columns[section][1]
        return str(section + 1)

    def row_dict(self, row_index: int) -> dict:
        return self._rows[row_index]
