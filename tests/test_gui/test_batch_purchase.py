"""GUI-тесты пакетного ввода (app/gui/tabs/batch_purchase.py).

quick_add_product() тестируется тем же приёмом, что и on_add()/on_edit()
у CRUD-вкладок: подменяем сам класс ProductDialog на фабрику, которая
создаёт диалог и сразу заполняет поля, плюс accept_dialogs патчит
QDialog.exec() глобально. Разница с тестами CRUD-вкладок в том, что
здесь патчится не метод make_*_dialog() на самом объекте, а символ
ProductDialog, импортированный в app.gui.tabs.batch_purchase — оттуда
quick_add_product() его и берёт.
"""

from app.crud import product_crud
from app.gui.tabs.batch_purchase import BatchPurchaseDialog, BatchRowWidget
from app.gui.tabs.common import set_combo_by_data
from app.service.crud_service import list_items
from PyQt6.QtWidgets import QDialog

# ---------- BatchRowWidget.values() ----------

def test_row_values_none_when_empty(qtbot):
    row = BatchRowWidget()
    qtbot.addWidget(row)

    assert row.values() is None


def test_row_values_when_filled(qtbot, product_vegetable):
    row = BatchRowWidget()
    qtbot.addWidget(row)

    set_combo_by_data(row.product_combo, product_vegetable.id)
    row.quantity_spin.setValue(3.0)
    row.price_spin.setValue(90.0)
    row.comment_edit.setText('  тест  ')

    assert row.values() == {
        'product_id': product_vegetable.id,
        'quantity': 3.0,
        'price': 90.0,
        'comment': 'тест',
    }


# ---------- управление строками ----------

def test_dialog_starts_with_two_rows(qtbot):
    dialog = BatchPurchaseDialog()
    qtbot.addWidget(dialog)

    assert len(dialog._rows) == 2


def test_add_row_appends_new_row(qtbot):
    dialog = BatchPurchaseDialog()
    qtbot.addWidget(dialog)

    dialog.add_row()

    assert len(dialog._rows) == 3


def test_remove_row_keeps_at_least_one(qtbot):
    dialog = BatchPurchaseDialog()
    qtbot.addWidget(dialog)

    dialog._remove_row(dialog._rows[0])
    assert len(dialog._rows) == 1

    # Пытаемся убрать последнюю оставшуюся строку — не должно пройти.
    dialog._remove_row(dialog._rows[0])
    assert len(dialog._rows) == 1


# ---------- _on_ok: валидация ----------

def test_on_ok_requires_store(qtbot, warning_calls):
    dialog = BatchPurchaseDialog()
    qtbot.addWidget(dialog)

    dialog._on_ok()

    assert dialog.result() != QDialog.DialogCode.Accepted
    assert warning_calls, 'ожидали предупреждение о невыбранном магазине'


def test_on_ok_requires_at_least_one_filled_row(
    qtbot, information_calls, single_store
):
    dialog = BatchPurchaseDialog()
    qtbot.addWidget(dialog)
    set_combo_by_data(dialog.store_combo, single_store.id)
    # Обе стартовые строки остаются пустыми — продукт нигде не выбран.

    dialog._on_ok()

    assert dialog.result() != QDialog.DialogCode.Accepted
    assert information_calls, (
        'ожидали подсказку добавить хотя бы одну заполненную строку'
    )


def test_on_ok_skips_empty_rows_and_keeps_filled_ones(
    qtbot, single_store, product_vegetable
):
    dialog = BatchPurchaseDialog()
    qtbot.addWidget(dialog)
    set_combo_by_data(dialog.store_combo, single_store.id)

    # Заполняем только первую из двух стартовых строк, вторую оставляем
    # пустой — она должна молча отсеяться, а не потребовать удаления.
    dialog._rows[0].quantity_spin.setValue(2.0)
    dialog._rows[0].price_spin.setValue(150.0)
    set_combo_by_data(dialog._rows[0].product_combo, product_vegetable.id)

    dialog._on_ok()

    assert dialog.result() == QDialog.DialogCode.Accepted
    values = dialog.values()
    assert values['store_id'] == single_store.id
    assert len(values['rows']) == 1
    assert values['rows'][0]['product_id'] == product_vegetable.id
    assert values['rows'][0]['quantity'] == 2.0
    assert values['rows'][0]['price'] == 150.0


# ---------- quick_add_product ----------

def test_quick_add_product_refreshes_all_rows(
    qtbot, accept_dialogs, monkeypatch, unit_kg
):
    dialog = BatchPurchaseDialog()
    qtbot.addWidget(dialog)

    def fake_product_dialog(parent=None):
        from app.gui.tabs.products import ProductDialog
        dlg = ProductDialog(parent)
        dlg.name_edit.setText('Новый продукт')
        set_combo_by_data(dlg.unit_combo, unit_kg.id)
        return dlg

    monkeypatch.setattr(
        'app.gui.tabs.batch_purchase.ProductDialog', fake_product_dialog
    )

    dialog.quick_add_product()

    products = list_items(product_crud, limit=100)
    new_product = next(p for p in products if p.name == 'Новый продукт')

    # Новый продукт должен появиться во ВСЕХ строках, а не только в той,
    # где его "затребовали" — ref_cache инвалидируется на весь диалог.
    for row in dialog._rows:
        assert row.product_combo.findData(new_product.id) != -1

    # И сразу выбран в последней строке.
    assert dialog._rows[-1].product_combo.currentData() == new_product.id


def test_quick_add_product_cancelled_changes_nothing(qtbot, monkeypatch):
    dialog = BatchPurchaseDialog()
    qtbot.addWidget(dialog)

    before = [row.product_combo.count() for row in dialog._rows]

    monkeypatch.setattr(
        'app.gui.tabs.batch_purchase.QDialog.exec',
        lambda self: QDialog.DialogCode.Rejected,
    )

    dialog.quick_add_product()

    after = [row.product_combo.count() for row in dialog._rows]
    assert after == before
