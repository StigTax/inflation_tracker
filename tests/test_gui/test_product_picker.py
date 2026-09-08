"""Тесты на ProductPickerWidget (app/gui/product_picker.py).

Изолированные тесты самого виджета — без AnalyticsWidget вокруг него.
Интеграция с AnalyticsWidget (переключение доступных товаров по
магазину/типу аналитики) — в test_analytics_widget.py.
"""

from app.gui.product_picker import ProductPickerWidget


class _FakeUnit:
    def __init__(self, measure_type: str, unit: str):
        self.measure_type = measure_type
        self.unit = unit


class _FakeProduct:
    def __init__(self, id_: int, name: str, unit=None):
        self.id = id_
        self.name = name
        self.unit = unit


def test_starts_empty(qtbot):
    picker = ProductPickerWidget()
    qtbot.addWidget(picker)

    assert picker.selected_ids() == []


def test_add_product_id_adds_to_selection(qtbot):
    picker = ProductPickerWidget()
    qtbot.addWidget(picker)
    picker.set_available_products([
        _FakeProduct(1, 'Яблоки'), _FakeProduct(2, 'Груши'),
    ])

    added = picker.add_product_id(1)

    assert added is True
    assert picker.selected_ids() == [1]


def test_add_product_id_not_in_available_returns_false(qtbot):
    picker = ProductPickerWidget()
    qtbot.addWidget(picker)
    picker.set_available_products([_FakeProduct(1, 'Яблоки')])

    added = picker.add_product_id(999)

    assert added is False
    assert picker.selected_ids() == []


def test_add_same_product_twice_is_idempotent(qtbot):
    picker = ProductPickerWidget()
    qtbot.addWidget(picker)
    picker.set_available_products([_FakeProduct(1, 'Яблоки')])

    picker.add_product_id(1)
    picker.add_product_id(1)

    assert picker.selected_ids() == [1]
    assert picker._list.count() == 1


def test_remove_id_removes_from_selection_and_list(qtbot):
    picker = ProductPickerWidget()
    qtbot.addWidget(picker)
    picker.set_available_products([_FakeProduct(1, 'Яблоки')])
    picker.add_product_id(1)

    picker._remove_id(1)

    assert picker.selected_ids() == []
    assert picker._list.count() == 0


def test_clear_removes_everything(qtbot):
    picker = ProductPickerWidget()
    qtbot.addWidget(picker)
    picker.set_available_products([
        _FakeProduct(1, 'Яблоки'), _FakeProduct(2, 'Груши'),
    ])
    picker.add_product_id(1)
    picker.add_product_id(2)

    picker.clear()

    assert picker.selected_ids() == []
    assert picker._list.count() == 0


def test_changed_signal_emitted_on_add_and_remove(qtbot):
    picker = ProductPickerWidget()
    qtbot.addWidget(picker)
    picker.set_available_products([_FakeProduct(1, 'Яблоки')])

    events = []
    picker.changed.connect(lambda: events.append(1))

    picker.add_product_id(1)
    picker._remove_id(1)

    assert len(events) == 2


def test_set_available_products_drops_stale_selection(qtbot):
    """Товар был выбран, но пропал из доступных (сменился магазин) —
    должен молча уйти из выбора, а не остаться "осиротевшим" ID."""
    picker = ProductPickerWidget()
    qtbot.addWidget(picker)
    picker.set_available_products([
        _FakeProduct(1, 'Яблоки'), _FakeProduct(2, 'Груши'),
    ])
    picker.add_product_id(1)
    picker.add_product_id(2)

    events = []
    picker.changed.connect(lambda: events.append(1))

    # Новый список доступных — только "Груши", "Яблок" там больше нет.
    picker.set_available_products([_FakeProduct(2, 'Груши')])

    assert picker.selected_ids() == [2]
    assert picker._list.count() == 1
    assert events, 'ожидали changed при вычищении осиротевшего выбора'


def test_set_available_products_keeps_selection_when_still_present(qtbot):
    picker = ProductPickerWidget()
    qtbot.addWidget(picker)
    picker.set_available_products([_FakeProduct(1, 'Яблоки')])
    picker.add_product_id(1)

    events = []
    picker.changed.connect(lambda: events.append(1))

    picker.set_available_products([
        _FakeProduct(1, 'Яблоки'), _FakeProduct(2, 'Груши'),
    ])

    assert picker.selected_ids() == [1]
    assert not events, 'без осиротевших ID changed эмитироваться не должен'


def test_label_includes_unit_when_present(qtbot):
    picker = ProductPickerWidget()
    qtbot.addWidget(picker)
    picker.set_available_products([
        _FakeProduct(1, 'Яблоки', unit=_FakeUnit('Вес', 'кг')),
    ])

    picker.add_product_id(1)

    assert picker._list.item(0).text() == 'Яблоки (Вес кг)'


def test_label_without_unit_is_just_name(qtbot):
    picker = ProductPickerWidget()
    qtbot.addWidget(picker)
    picker.set_available_products([_FakeProduct(1, 'Яблоки')])

    picker.add_product_id(1)

    assert picker._list.item(0).text() == 'Яблоки'
