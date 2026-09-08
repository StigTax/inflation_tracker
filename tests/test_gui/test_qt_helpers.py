"""Тесты на app/gui/qt_helpers.py::setup_searchable_combo().

Регрессия: editable QComboBox по умолчанию использует sizeAdjustPolicy
AdjustToContentsOnFirstShow — ширина считается по самому длинному
пункту модели один раз при первом показе и дальше не пересчитывается
стабильно. С длинными названиями продуктов это раздувало строку в
BatchPurchaseDialog так, что кнопка удаления строки уезжала за пределы
видимой области QScrollArea (и появлялась только при растягивании
окна руками).
"""

from app.gui.qt_helpers import setup_searchable_combo
from PyQt6.QtWidgets import QComboBox


def test_setup_searchable_combo_uses_stable_size_adjust_policy(qtbot):
    combo = QComboBox()
    qtbot.addWidget(combo)

    setup_searchable_combo(combo, placeholder='Начни печатать…')

    assert combo.sizeAdjustPolicy() == (
        QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
    )


def test_setup_searchable_combo_width_does_not_depend_on_longest_item(qtbot):
    """Главная проверка регрессии: ширина не скачет от содержимого модели.

    Без фикса добавление очень длинного пункта в уже показанный
    комбобокс меняло бы sizeHint (AdjustToContentsOnFirstShow держится
    за первый расчёт, но последующие reload_products() с другим
    содержимым моделирует именно нестабильность, которую видел Никита).
    """
    combo = QComboBox()
    qtbot.addWidget(combo)
    setup_searchable_combo(combo, min_contents_chars=24)

    combo.addItem('Молоко (Объем л)')
    width_before = combo.minimumSizeHint().width()

    combo.addItem(
        'Очень-очень длинное название продукта с уточнением бренда '
        'и объёма упаковки для проверки регрессии (Вес кг)'
    )
    width_after = combo.minimumSizeHint().width()

    assert width_before == width_after


def test_setup_searchable_combo_respects_custom_min_contents_chars(qtbot):
    narrow = QComboBox()
    wide = QComboBox()
    qtbot.addWidget(narrow)
    qtbot.addWidget(wide)

    setup_searchable_combo(narrow, min_contents_chars=8)
    setup_searchable_combo(wide, min_contents_chars=40)

    assert (
        narrow.minimumSizeHint().width() < wide.minimumSizeHint().width()
    )


def test_setup_searchable_combo_sets_placeholder_on_line_edit(qtbot):
    combo = QComboBox()
    qtbot.addWidget(combo)

    setup_searchable_combo(combo, placeholder='Начни печатать продукт…')

    assert combo.lineEdit() is not None
    assert combo.lineEdit().placeholderText() == 'Начни печатать продукт…'


def test_setup_searchable_combo_makes_combo_editable_with_completer(qtbot):
    combo = QComboBox()
    qtbot.addWidget(combo)

    setup_searchable_combo(combo)

    assert combo.isEditable() is True
    assert combo.completer() is not None
