"""GUI-тесты пакетного ввода (app/gui/tabs/batch_purchase.py).

quick_add_product() тестируется тем же приёмом, что и on_add()/on_edit()
у CRUD-вкладок: подменяем сам класс ProductDialog на фабрику, которая
создаёт диалог и сразу заполняет поля, плюс accept_dialogs патчит
QDialog.exec() глобально. Разница с тестами CRUD-вкладок в том, что
здесь патчится не метод make_*_dialog() на самом объекте, а символ
ProductDialog, импортированный в app.gui.tabs.batch_purchase — оттуда
quick_add_product() его и берёт.
"""

from datetime import date

import pytest
from app.crud import product_crud
from app.gui.tabs.batch_purchase import BatchPurchaseDialog, BatchRowWidget
from app.gui.tabs.common import set_combo_by_data
from app.models import Product
from app.service import crud_service
from app.service.crud_service import list_items
from PyQt6.QtWidgets import QDialog

# ---------- BatchRowWidget.values() ----------

def test_row_values_none_when_empty(qtbot):
    row = BatchRowWidget()
    qtbot.addWidget(row)

    assert row.values() is None


def test_row_width_stays_bounded_with_long_product_name(
    qtbot, category_food, unit_kg
):
    """Регрессия: длинное название продукта раздувало product_combo и
    выталкивало кнопку удаления строки (✕) за пределы диалога — она
    "появлялась" только если руками растянуть окно. Корень — дефолтный
    sizeAdjustPolicy editable-комбобокса, фикс — в setup_searchable_combo()
    (app/gui/qt_helpers.py), здесь проверяем эффект на реальной строке.
    """
    long_name_product = crud_service.create_item(
        product_crud,
        Product(
            name=(
                'Очень длинное название продукта с уточнением бренда, '
                'вкуса и объёма упаковки специально для теста на ширину'
            ),
            category_id=category_food.id,
            unit_id=unit_kg.id,
        ),
    )

    row = BatchRowWidget()
    qtbot.addWidget(row)
    row.reload_products()  # длинное название теперь есть в модели

    set_combo_by_data(row.product_combo, long_name_product.id)

    # Кнопка удаления — фиксированной ширины и не должна ужиматься
    # или "теряться" из-за соседнего комбобокса.
    assert row.btn_remove.width() == 28
    # Комбобокс не обязан вмещать имя целиком — именно это и раздувало
    # строку раньше; минимальная ширина должна оставаться в разумных
    # пределах независимо от длины названия.
    assert row.product_combo.minimumSizeHint().width() < 400


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


# ---------- prefill (повторить последний чек) ----------

def test_prefill_creates_rows_from_receipt_instead_of_two_empty(
    qtbot, single_store, product_vegetable, product_no_category,
):
    prefill = {
        'store_id': single_store.id,
        'purchase_date': date(2024, 1, 1),
        'rows': [
            {
                'product_id': product_vegetable.id,
                'quantity': 2.0,
                'price': 150.0,
            },
            {
                'product_id': product_no_category.id,
                'quantity': 1.0,
                'price': 60.0,
            },
        ],
    }

    dialog = BatchPurchaseDialog(prefill=prefill)
    qtbot.addWidget(dialog)

    assert len(dialog._rows) == 2
    assert dialog.store_combo.currentData() == single_store.id

    values_by_product = {
        row.product_combo.currentData(): row for row in dialog._rows
    }
    row_a = values_by_product[product_vegetable.id]
    assert row_a.quantity_spin.value() == pytest.approx(2.0)
    assert row_a.price_spin.value() == pytest.approx(150.0)

    row_b = values_by_product[product_no_category.id]
    assert row_b.quantity_spin.value() == pytest.approx(1.0)
    assert row_b.price_spin.value() == pytest.approx(60.0)


def test_prefill_date_defaults_to_today_not_old_receipt_date(
    qtbot, single_store, product_vegetable,
):
    """Повторяем покупку сегодня, а не переписываем историю задним
    числом — дата чека всегда предлагается сегодняшней, даже если
    prefill пришёл из старого чека."""
    prefill = {
        'store_id': single_store.id,
        'purchase_date': date(2020, 1, 1),
        'rows': [{
            'product_id': product_vegetable.id,
            'quantity': 1.0,
            'price': 10.0,
        }],
    }

    dialog = BatchPurchaseDialog(prefill=prefill)
    qtbot.addWidget(dialog)

    assert dialog.date_edit.date().toPyDate() == date.today()


def test_prefill_empty_rows_still_starts_with_two_empty_rows(qtbot):
    """Если "последнего чека" по факту нет, prefill с пустым rows не
    должен привести к диалогу без единой строки."""
    dialog = BatchPurchaseDialog(prefill={'store_id': None, 'rows': []})
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
