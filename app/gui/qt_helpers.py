from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QComboBox, QCompleter


def setup_searchable_combo(
    combo: QComboBox,
    *,
    placeholder: str = '',
    min_contents_chars: int = 24,
) -> None:
    """Делает QComboBox удобным для поиска по вводу.

    Поведение:
    - пользователь может печатать в поле
    - выпадает список подсказок
    - поиск по подстроке, без учёта регистра

    Отдельно фиксируем ширину политикой AdjustToMinimumContentsLength
    вместо дефолтной для editable-комбобокса AdjustToContentsOnFirstShow:
    та считает ширину по самому длинному пункту модели один раз при
    первом показе и дальше не пересчитывает стабильно — если в списке
    попадается длинное название продукта, комбобокс (а с ним и вся
    строка в layout) раздувается непредсказуемо и по-разному в разных
    местах, где переиспользуется этот хелпер.

    Args:
        combo: Комбо-бокс, который нужно настроить.
        placeholder: Плейсхолдер для lineEdit.
        min_contents_chars: Ширина комбобокса в "символах" — стабильная
            база, не зависящая от того, что сейчас лежит в модели.
    """
    combo.setEditable(True)
    combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
    combo.setSizeAdjustPolicy(
        QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
    )
    combo.setMinimumContentsLength(min_contents_chars)

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
