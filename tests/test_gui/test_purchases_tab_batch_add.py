"""Тесты на связку PurchasesTab.on_batch_add() -> BatchPurchaseDialog ->
create_purchases_batch().

Внутреннее поведение самого BatchPurchaseDialog уже покрыто в
test_batch_purchase.py. Здесь проверяем только "монтаж": вкладка
правильно передаёт данные из диалога в сервис и обновляется по
результату. Поэтому вместо реального BatchPurchaseDialog подставляем
лёгкий стаб с готовыми values() — не нужно тащить в тест реальные
виджеты диалога ради проверки трёх строк кода в on_batch_add().
"""

from datetime import date

from app.gui.tabs.purchases import PurchasesTab
from PyQt6.QtWidgets import QDialog


class _StubBatchDialog:
    """Минимальная замена BatchPurchaseDialog: exec() + values()."""

    def __init__(self, canned_values, accepted=True):
        self._canned_values = canned_values
        self._accepted = accepted

    def __call__(self, parent=None):
        # on_batch_add() вызывает BatchPurchaseDialog(self) как конструктор
        # класса — эмулируем это, возвращая тот же (уже настроенный) стаб.
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
