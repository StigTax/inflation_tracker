from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QComboBox, QCompleter


def setup_searchable_combo(
    combo: QComboBox,
    *,
    placeholder: str = '',
) -> None:
    """Делает QComboBox удобным для поиска по вводу.

    Поведение:
    - пользователь может печатать в поле
    - выпадает список подсказок
    - поиск по подстроке, без учёта регистра

    Args:
        combo: Комбо-бокс, который нужно настроить.
        placeholder: Плейсхолдер для lineEdit.
    """
    combo.setEditable(True)
    combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)

    le = combo.lineEdit()
    if le and placeholder:
        le.setPlaceholderText(placeholder)

    completer = QCompleter(combo.model(), combo)
    completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
    completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
    completer.setFilterMode(Qt.MatchFlag.MatchContains)

    def _activate(text: str) -> None:
        idx = combo.findText(text, Qt.MatchFlag.MatchExactly)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    completer.activated[str].connect(_activate)
    combo.setCompleter(completer)
