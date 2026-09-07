"""GUI-тесты для PurchaseDialog (app/gui/tabs/purchases.py).

Ключевая идея: диалог за данными для комбобоксов продукта/магазина
ходит через list_items_safe -> app.service.crud_service.list_items,
а эта функция уже патчится в conftest.py (override_get_session).
Поэтому никакой отдельной изоляции БД для GUI-тестов городить не
пришлось — используем те же фикстуры (product_vegetable, few_stores),
что и в test_service/.
"""

from app.gui.tabs.purchases import PurchaseDialog
from PyQt6.QtWidgets import QDialog

# ---------- values(): happy path ----------


def test_values_happy_path(filled_dialog, product_vegetable, few_stores):
    """Без промо values() отдаёт ровно то, что ввели, без сюрпризов."""
    values = filled_dialog.values()

    assert values['product_id'] == product_vegetable.id
    assert values['store_id'] == few_stores[0].id
    assert values['quantity'] == 2.0
    assert values['total_price'] == 150.0
    assert values['is_promo'] is False
    assert values['promo_type'] is None
    assert values['regular_unit_price'] is None


def test_values_with_promo(filled_dialog):
    """При включённой 'Акции' в values() попадают promo_type и regular_price.

    Меняем состояние виджетов напрямую (setChecked/setCurrentIndex/
    setValue), а не эмулируем клики мышкой через qtbot.mouseClick.
    Виджеты в этом диалоге завязаны на сигналы (stateChanged,
    valueChanged), а не на геометрию клика — так что прямой вызов
    сеттера надёжнее и не зависит от того, попал ли "клик" в нужный
    пиксель на offscreen-платформе.
    """
    filled_dialog.is_promo_check.setChecked(True)

    idx = filled_dialog.promo_type_combo.findData('discount')
    filled_dialog.promo_type_combo.setCurrentIndex(idx)
    filled_dialog.regular_price_spin.setValue(120.0)

    values = filled_dialog.values()

    assert values['is_promo'] is True
    assert values['promo_type'] == 'discount'
    assert values['regular_unit_price'] == 120.0


# ---------- _toggle_promo_fields ----------

def test_promo_fields_disabled_by_default(empty_dialog):
    """Пока 'Акция' не отмечена — promo_type и regular_price недоступны."""
    assert empty_dialog.is_promo_check.isChecked() is False
    assert empty_dialog.promo_type_combo.isEnabled() is False
    assert empty_dialog.regular_price_spin.isEnabled() is False


def test_promo_fields_enabled_on_check(empty_dialog):
    """Включение чекбокса 'Акция' сразу активирует промо-поля."""
    empty_dialog.is_promo_check.setChecked(True)

    assert empty_dialog.promo_type_combo.isEnabled() is True
    assert empty_dialog.regular_price_spin.isEnabled() is True


# ---------- _update_unit_price ----------

def test_unit_price_label_recalculates(filled_dialog):
    """Лейбл цены за единицу пересчитывается при смене кол-ва/суммы."""
    filled_dialog.quantity_spin.setValue(2.0)
    filled_dialog.price_spin.setValue(100.0)

    assert filled_dialog.unit_price_label.text() == 'Цена за единицу: 50.00'


# ---------- _on_ok: валидация ----------

def test_on_ok_blocks_without_product(empty_dialog, warning_calls):
    """Без выбранного продукта форма не принимается, пользователю — варнинг."""
    empty_dialog._on_ok()

    assert empty_dialog.result() != QDialog.DialogCode.Accepted
    assert warning_calls, 'ожидали предупреждение о невыбранном продукте'


def test_on_ok_blocks_without_store(qtbot, product_vegetable, warning_calls):
    """Продукт выбран, магазин — нет: тоже блокируем."""
    dlg = PurchaseDialog(product_id=product_vegetable.id)
    qtbot.addWidget(dlg)

    dlg._on_ok()

    assert dlg.result() != QDialog.DialogCode.Accepted
    assert warning_calls, 'ожидали предупреждение о невыбранном магазине'


def test_on_ok_accepts_with_product_and_store(filled_dialog):
    """Продукт и магазин выбраны — форма принимается без предупреждений."""
    filled_dialog._on_ok()

    assert filled_dialog.result() == QDialog.DialogCode.Accepted
