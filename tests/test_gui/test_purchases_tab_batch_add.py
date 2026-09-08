"""Тесты на связку PurchasesTab.on_batch_add()/on_repeat_last_receipt() ->
BatchPurchaseDialog -> create_purchases_batch().

Внутреннее поведение самого BatchPurchaseDialog (включая prefill) уже
покрыто в test_batch_purchase.py. Здесь проверяем только "монтаж":
вкладка правильно передаёт данные из диалога в сервис и обновляется по
результату. Поэтому вместо реального BatchPurchaseDialog подставляем
лёгкий стаб с готовыми values() — не нужно тащить в тест реальные
виджеты диалога ради проверки нескольких строк кода в методах вкладки.
"""

from datetime import date

from app.gui.tabs.purchases import PurchasesTab
from PyQt6.QtWidgets import QDialog


class _StubBatchDialog:
    """Минимальная замена BatchPurchaseDialog: exec() + values().

    Дополнительно запоминает prefill, с которым его "сконструировали" —
    нужно для on_repeat_last_receipt(), которая вызывает
    BatchPurchaseDialog(self, prefill=...).
    """

    def __init__(self, canned_values, accepted=True):
        self._canned_values = canned_values
        self._accepted = accepted
        self.received_prefill = None

    def __call__(self, parent=None, *, prefill=None):
        # on_batch_add()/on_repeat_last_receipt() вызывают
        # BatchPurchaseDialog(self, ...) как конструктор класса —
        # эмулируем это, возвращая тот же (уже настроенный) стаб.
        self.received_prefill = prefill
        return self

    def exec(self):
        return (
            QDialog.DialogCode.Accepted
            if self._accepted
            else QDialog.DialogCode.Rejected
        )

    def values(self):
        return self._canned_values


def test_on_batch_add_creates_purchases_and_reloads(
    qtbot, monkeypatch, single_store, product_vegetable, information_calls
):
    tab = PurchasesTab()
    qtbot.addWidget(tab)

    stub = _StubBatchDialog({
        'store_id': single_store.id,
        'purchase_date': date(2024, 6, 1),
        'rows': [
            {
                'product_id': product_vegetable.id,
                'quantity': 2.0,
                'price': 100.0,
                'comment': None,
            },
        ],
    })
    monkeypatch.setattr('app.gui.tabs.purchases.BatchPurchaseDialog', stub)

    tab.on_batch_add()

    assert tab._total == 1
    assert information_calls, 'ожидали "Готово" после успешного сохранения'


def test_on_batch_add_cancelled_creates_nothing(
    qtbot, monkeypatch, single_store, product_vegetable
):
    tab = PurchasesTab()
    qtbot.addWidget(tab)

    stub = _StubBatchDialog(
        {
            'store_id': single_store.id,
            'purchase_date': date(2024, 6, 1),
            'rows': [{
                'product_id': product_vegetable.id,
                'quantity': 1.0,
                'price': 10.0,
                'comment': None,
            }],
        },
        accepted=False,
    )
    monkeypatch.setattr('app.gui.tabs.purchases.BatchPurchaseDialog', stub)

    tab.on_batch_add()

    assert tab._total == 0


def test_on_batch_add_shows_error_and_does_not_reload_partially(
    qtbot, monkeypatch, single_store, product_vegetable, critical_calls
):
    """Невалидная партия (отрицательное количество) не должна создать
    ни одной покупки — это тот же атомарный контракт service-слоя,
    только проверенный теперь и через реальный клик по кнопке вкладки.
    """
    tab = PurchasesTab()
    qtbot.addWidget(tab)

    stub = _StubBatchDialog({
        'store_id': single_store.id,
        'purchase_date': date(2024, 6, 1),
        'rows': [{
            'product_id': product_vegetable.id,
            'quantity': -1.0,
            'price': 10.0,
            'comment': None,
        }],
    })
    monkeypatch.setattr('app.gui.tabs.purchases.BatchPurchaseDialog', stub)

    tab.on_batch_add()

    assert critical_calls, 'ожидали сообщение об ошибке при невалидной партии'
    assert tab._total == 0


# ---------- on_repeat_last_receipt ----------

def test_on_repeat_last_receipt_shows_information_when_nothing_to_repeat(
    qtbot, monkeypatch, single_store, product_vegetable, information_calls
):
    """Товар и магазин уже есть, но ни одной покупки ещё не создано —
    повторять нечего, диалог открываться не должен вовсе."""
    tab = PurchasesTab()
    qtbot.addWidget(tab)

    def fail_if_called(*args, **kwargs):
        raise AssertionError(
            'BatchPurchaseDialog не должен открываться без чеков'
        )

    monkeypatch.setattr(
        'app.gui.tabs.purchases.BatchPurchaseDialog', fail_if_called
    )

    tab.on_repeat_last_receipt()

    assert information_calls, 'ожидали подсказку "нечего повторять"'
    assert tab._total == 0


def test_on_repeat_last_receipt_opens_dialog_with_last_receipt_as_prefill(
    qtbot, monkeypatch, single_store, product_vegetable, information_calls
):
    from app.service import purchases as purchases_service

    purchases_service.create_purchases_batch(
        store_id=single_store.id,
        purchase_date=date(2024, 1, 1),
        rows=[{
            'product_id': product_vegetable.id,
            'quantity': 2.0,
            'price': 150.0,
        }],
    )

    tab = PurchasesTab()
    qtbot.addWidget(tab)

    stub = _StubBatchDialog({
        'store_id': single_store.id,
        'purchase_date': date.today(),
        'rows': [{
            'product_id': product_vegetable.id,
            'quantity': 2.0,
            'price': 150.0,
            'comment': None,
        }],
    })
    monkeypatch.setattr('app.gui.tabs.purchases.BatchPurchaseDialog', stub)

    tab.on_repeat_last_receipt()

    # Проверяем и то, что диалог сконструирован именно с prefill от
    # get_last_receipt(), и то, что после accept партия реально создана.
    assert stub.received_prefill == {
        'store_id': single_store.id,
        'purchase_date': date(2024, 1, 1),
        'rows': [{
            'product_id': product_vegetable.id,
            'quantity': 2.0,
            'price': 150.0,
        }],
    }
    # 1 покупка была создана до открытия вкладки (её и "повторяем") +
    # 1 новая из canned-values стаба после accept — итого 2.
    assert tab._total == 2
    assert information_calls, 'ожидали "Готово" после успешного сохранения'
