"""GUI-тесты пагинации PurchasesTab (app/gui/tabs/purchases.py).

PURCHASES_PAGE_SIZE = 25 (app/core/constants.py). many_purchases создаёт
30 записей — на 5 больше страницы, чтобы вторая (неполная) страница
реально проверялась, а не совпадала по размеру с первой случайно.
"""

from datetime import date, timedelta

import pytest
from app.core.constants import PURCHASES_PAGE_SIZE
from app.gui.tabs.common import set_combo_by_data
from app.gui.tabs.purchases import PurchasesTab
from app.service import purchases as purchases_service


@pytest.fixture
def many_purchases(product_vegetable, single_store):
    created = []
    for i in range(30):
        p = purchases_service.create_purchase(
            store_id=single_store.id,
            product_id=product_vegetable.id,
            quantity=1.0,
            price=100.0 + i,
            purchase_date=date(2024, 1, 1) + timedelta(days=i),
        )
        created.append(p)
    return created


@pytest.fixture
def purchases_tab(qtbot, many_purchases):
    tab = PurchasesTab()
    qtbot.addWidget(tab)
    return tab


def test_initial_page_shows_page_size_rows(purchases_tab):
    assert purchases_tab._page == 0
    assert purchases_tab._total == 30
    assert purchases_tab.model.rowCount() == PURCHASES_PAGE_SIZE
    assert purchases_tab.count_label.text() == 'Показано 1–25 из 30'
    assert purchases_tab.page_label.text() == 'Стр. 1 из 2'


def test_prev_button_disabled_on_first_page(purchases_tab):
    assert purchases_tab.btn_prev_page.isEnabled() is False
    assert purchases_tab.btn_next_page.isEnabled() is True


def test_next_page_shows_remaining_rows(purchases_tab):
    purchases_tab._go_next_page()

    assert purchases_tab._page == 1
    assert purchases_tab.model.rowCount() == 5
    assert purchases_tab.count_label.text() == 'Показано 26–30 из 30'
    assert purchases_tab.page_label.text() == 'Стр. 2 из 2'


def test_next_button_disabled_on_last_page(purchases_tab):
    purchases_tab._go_next_page()

    assert purchases_tab.btn_next_page.isEnabled() is False
    assert purchases_tab.btn_prev_page.isEnabled() is True


def test_go_next_page_noop_on_last_page(purchases_tab):
    """Повторный клик 'Вперёд' на последней странице ничего не меняет."""
    purchases_tab._go_next_page()
    purchases_tab._go_next_page()

    assert purchases_tab._page == 1
    assert purchases_tab.model.rowCount() == 5


def test_go_prev_page_noop_on_first_page(purchases_tab):
    """Клик 'Назад' на первой странице ничего не меняет."""
    purchases_tab._go_prev_page()

    assert purchases_tab._page == 0
    assert purchases_tab.model.rowCount() == PURCHASES_PAGE_SIZE


def test_apply_filters_resets_to_first_page(
    purchases_tab, product_vegetable
):
    """Смена фильтра сбрасывает страницу — иначе можно словить пустую
    таблицу, если под новый фильтр страниц меньше, чем текущая.
    """
    purchases_tab._go_next_page()
    assert purchases_tab._page == 1

    set_combo_by_data(
        purchases_tab.filter_product_combo, product_vegetable.id
    )
    purchases_tab.on_apply_filters()

    assert purchases_tab._page == 0
    assert purchases_tab.model.rowCount() == PURCHASES_PAGE_SIZE


def test_reset_filters_resets_to_first_page(purchases_tab):
    purchases_tab._go_next_page()
    assert purchases_tab._page == 1

    purchases_tab.on_reset_filters()

    assert purchases_tab._page == 0


def test_page_clamps_after_deleting_all_rows_on_last_page(
    purchases_tab, confirm_dialog
):
    """Удаляем все 5 записей со второй страницы — страниц становится
    меньше, и текущая страница должна схлопнуться на первую сама,
    а не показать пустую таблицу.
    """
    purchases_tab._go_next_page()
    assert purchases_tab._page == 1
    assert purchases_tab.model.rowCount() == 5

    confirm_dialog(True)
    for _ in range(5):
        purchases_tab.table.setCurrentIndex(
            purchases_tab.table.model().index(0, 0)
        )
        purchases_tab.on_delete()

    assert purchases_tab._total == 25
    assert purchases_tab._page == 0
    assert purchases_tab.model.rowCount() == 25


def test_empty_state_shows_zero_and_disables_navigation(qtbot):
    """Без единой покупки — корректный нулевой стейт, а не деление на 0."""
    tab = PurchasesTab()
    qtbot.addWidget(tab)

    assert tab._total == 0
    assert tab.model.rowCount() == 0
    assert tab.count_label.text() == 'Показано 0–0 из 0'
    assert tab.page_label.text() == 'Стр. 1 из 1'
    assert tab.btn_prev_page.isEnabled() is False
    assert tab.btn_next_page.isEnabled() is False
