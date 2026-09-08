"""GUI-тесты фоновой аналитики (app/gui/analytics.py).

В отличие от test_background_task_runner.py, здесь проверяем не сам
механизм потока, а то, что AnalyticsWidget правильно им пользуется:
блокирует кнопку на время расчёта, отрисовывает график по готовности,
показывает QMessageBox.critical при падении и не виснет при закрытии
окна посреди расчёта.

svc.product_inflation_index() внутри AnalyticsWidget.build() вызывается
как app.service.analytics.product_inflation_index (import as svc в
analytics.py — это тот же объект модуля, поэтому патчить нужно именно
'app.service.analytics.product_inflation_index', а не что-то в
app.gui.analytics).
"""

import threading
from datetime import date

import pytest
from app.gui.analytics import AnalyticsWidget
from app.service import purchases


@pytest.fixture
def analytics_widget(qtbot, purchase_product):
    widget = AnalyticsWidget()
    qtbot.addWidget(widget)
    return widget


def _select_product(widget: AnalyticsWidget, product_id: int) -> None:
    widget.kind_combo.setCurrentIndex(
        widget.kind_combo.findData('product_index')
    )
    widget.product_combo.setCurrentIndex(
        widget.product_combo.findData(product_id)
    )


def _select_category(widget: AnalyticsWidget, category_id: int) -> None:
    widget.kind_combo.setCurrentIndex(
        widget.kind_combo.findData('category_index')
    )
    widget.category_combo.setCurrentIndex(
        widget.category_combo.findData(category_id)
    )


def _select_store(widget: AnalyticsWidget, store_id: int) -> None:
    widget.kind_combo.setCurrentIndex(
        widget.kind_combo.findData('store_index')
    )
    widget.store_combo.setCurrentIndex(
        widget.store_combo.findData(store_id)
    )


def _select_basket(
    widget: AnalyticsWidget, product_ids: list = (),
) -> None:
    widget.kind_combo.setCurrentIndex(
        widget.kind_combo.findData('basket_index')
    )
    for product_id in product_ids:
        widget.product_picker.add_product_id(product_id)


def test_build_runs_in_background_and_replots(
    qtbot, analytics_widget, product_vegetable
):
    """Пока расчёт идёт — кнопка недоступна, по готовности график обновлён."""
    _select_product(analytics_widget, product_vegetable.id)

    analytics_widget.build()

    # Сразу после клика поток мог ещё не успеть стартовать, но кнопка
    # должна быть задизейблена уже к этому моменту — _set_busy(True)
    # вызывается синхронно, до фактического запуска QThread.
    assert analytics_widget.btn_build.isEnabled() is False
    assert analytics_widget.kpi.text() == 'Считаю…'

    qtbot.waitUntil(
        lambda: analytics_widget.btn_build.isEnabled(), timeout=2000
    )
    assert analytics_widget.btn_build.text() == 'Построить'
    assert analytics_widget.kpi.text() != 'Считаю…'


def test_build_shows_error_and_recovers_on_failure(
    qtbot, analytics_widget, product_vegetable, monkeypatch, critical_calls
):
    """Падение расчёта в фоне не морозит кнопку и не убивает виджет."""

    def boom(**kwargs):
        raise RuntimeError('расчёт сломался')

    monkeypatch.setattr(
        'app.service.analytics.product_inflation_index', boom
    )

    _select_product(analytics_widget, product_vegetable.id)
    analytics_widget.build()

    qtbot.waitUntil(
        lambda: analytics_widget.btn_build.isEnabled(), timeout=2000
    )
    assert critical_calls, 'ожидали QMessageBox.critical при ошибке расчёта'
    assert analytics_widget.kpi.text() == 'Ошибка при построении.'


def test_second_click_while_running_is_ignored(
    qtbot, analytics_widget, product_vegetable, monkeypatch
):
    """Повторный build() поверх ещё не завершённого — no-op, не гонка.

    В реальном UI это защищено задизейбленной кнопкой, но проверяем
    логику build()/_run_analytics() напрямую, в обход клика мышкой —
    так тест не зависит от того, реально ли Qt блокирует клик по
    задизейбленной кнопке на конкретной платформе.
    """
    release = threading.Event()
    calls = []

    def slow(**kwargs):
        calls.append(1)
        release.wait(timeout=2)
        return {'points': [], 'kpi': None}

    monkeypatch.setattr(
        'app.service.analytics.product_inflation_index', slow
    )

    _select_product(analytics_widget, product_vegetable.id)

    analytics_widget.build()
    analytics_widget.build()  # тот самый повторный вызов "поверх"

    # Ключевая проверка: пока первая (настоящая) задача ещё не
    # завершилась, кнопка обязана оставаться недоступной. Если бы
    # _run_analytics() по ветке "не удалось запустить" снимал busy —
    # тут кнопка была бы снова доступна, хотя расчёт всё ещё идёт.
    assert analytics_widget.btn_build.isEnabled() is False

    release.set()
    qtbot.waitUntil(
        lambda: analytics_widget.btn_build.isEnabled(), timeout=2000
    )

    assert len(calls) == 1, 'fn должна была стартовать только один раз'


def test_shutdown_waits_for_background_calculation(
    qtbot, analytics_widget, product_vegetable, monkeypatch
):
    """shutdown() дожидается расчёта — ровно то, что вызывает closeEvent.

    Без этого закрытие окна посреди построения графика роняло бы
    процесс с "QThread: Destroyed while thread is still running".
    """
    release = threading.Event()

    def slow(**kwargs):
        release.wait(timeout=2)
        return {'points': [], 'kpi': None}

    monkeypatch.setattr(
        'app.service.analytics.product_inflation_index', slow
    )

    _select_product(analytics_widget, product_vegetable.id)
    analytics_widget.build()
    assert analytics_widget.btn_build.isEnabled() is False

    release.set()
    analytics_widget.shutdown()  # не должно зависнуть или упасть

    assert analytics_widget._task_runner.is_running() is False


# ---------- регрессия: корзина товаров для store_index ----------
# (AttributeError: 'AnalyticsWidget' object has no attribute
# 'product_ids_edit' — виджет был проброшен в _parse_ids()/build(), но
# никогда не создавался и не клался в форму; сейчас это уже другой
# виджет — ProductPickerWidget, но регрессия на "пусто = все товары"
# всё ещё актуальна)

def test_store_index_builds_without_basket_filter(
    qtbot, analytics_widget, few_stores, monkeypatch
):
    calls = []

    def fake_store_index(**kwargs):
        calls.append(kwargs)
        return {'points': [], 'kpi': None}

    monkeypatch.setattr(
        'app.service.analytics.store_inflation_index', fake_store_index
    )

    _select_store(analytics_widget, few_stores[0].id)
    assert analytics_widget.product_picker.selected_ids() == []

    analytics_widget.build()

    qtbot.waitUntil(
        lambda: analytics_widget.btn_build.isEnabled(), timeout=2000
    )
    assert len(calls) == 1
    assert calls[0]['product_ids'] is None


def test_store_index_basket_shows_only_products_sold_at_that_store(
    qtbot, analytics_widget, few_stores, few_products, monkeypatch
):
    """Ключевое требование: в корзину для store_index можно добавить
    только товары, которые реально покупались в ЭТОМ магазине — а не
    весь каталог. Меньше листания, меньше шанс промахнуться мимо
    релевантного товара.
    """
    store = few_stores[0]
    sold_here, never_sold_here = few_products[0], few_products[1]

    purchases.create_purchase(
        store_id=store.id, product_id=sold_here.id,
        quantity=1.0, price=10.0, purchase_date=date(2024, 1, 1),
    )

    calls = []

    def fake_store_index(**kwargs):
        calls.append(kwargs)
        return {'points': [], 'kpi': None}

    monkeypatch.setattr(
        'app.service.analytics.store_inflation_index', fake_store_index
    )

    _select_store(analytics_widget, store.id)

    assert analytics_widget.product_picker.add_product_id(sold_here.id)
    assert not analytics_widget.product_picker.add_product_id(
        never_sold_here.id
    )

    analytics_widget.build()

    qtbot.waitUntil(
        lambda: analytics_widget.btn_build.isEnabled(), timeout=2000
    )
    assert len(calls) == 1
    assert calls[0]['product_ids'] == [sold_here.id]


def test_store_index_basket_choices_refresh_when_store_changes(
    analytics_widget, few_stores, product_vegetable,
):
    """Смена магазина при активном store_index тут же обновляет список
    товаров, доступных для добавления в корзину-фильтр."""
    store_with_sales, store_without_sales = few_stores[0], few_stores[1]
    purchases.create_purchase(
        store_id=store_with_sales.id, product_id=product_vegetable.id,
        quantity=1.0, price=10.0, purchase_date=date(2024, 1, 1),
    )

    _select_store(analytics_widget, store_with_sales.id)
    assert analytics_widget.product_picker.add_product_id(
        product_vegetable.id
    )

    _select_store(analytics_widget, store_without_sales.id)
    assert analytics_widget.product_picker.selected_ids() == [], (
        'товар без покупок в новом магазине должен был отсеяться'
    )
    assert not analytics_widget.product_picker.add_product_id(
        product_vegetable.id
    ), 'в магазине без продаж этого товара его нельзя добавить заново'


# ---------- index_method: Ласпейрес/Пааше/Фишер ----------

def test_index_method_combo_enabled_only_for_category_and_store(
    analytics_widget, product_vegetable, category_food, few_stores,
):
    """Метод индекса имеет смысл только там, где в корзине > 1 товара."""
    _select_product(analytics_widget, product_vegetable.id)
    assert analytics_widget.index_method_combo.isEnabled() is False

    _select_category(analytics_widget, category_food.id)
    assert analytics_widget.index_method_combo.isEnabled() is True

    _select_store(analytics_widget, few_stores[0].id)
    assert analytics_widget.index_method_combo.isEnabled() is True


def test_index_method_resets_to_laspeyres_when_switching_to_product(
    analytics_widget, product_vegetable, category_food,
):
    _select_category(analytics_widget, category_food.id)
    analytics_widget.index_method_combo.setCurrentIndex(
        analytics_widget.index_method_combo.findData('fisher')
    )
    assert analytics_widget.index_method_combo.currentData() == 'fisher'

    _select_product(analytics_widget, product_vegetable.id)

    assert analytics_widget.index_method_combo.currentData() == 'laspeyres'


def test_category_index_passes_selected_index_method_to_service(
    qtbot, analytics_widget, category_food, monkeypatch
):
    calls = []

    def fake_category_index(**kwargs):
        calls.append(kwargs)
        return {'points': [], 'kpi': None}

    monkeypatch.setattr(
        'app.service.analytics.category_inflation_index',
        fake_category_index,
    )

    _select_category(analytics_widget, category_food.id)
    analytics_widget.index_method_combo.setCurrentIndex(
        analytics_widget.index_method_combo.findData('paasche')
    )

    analytics_widget.build()

    qtbot.waitUntil(
        lambda: analytics_widget.btn_build.isEnabled(), timeout=2000
    )
    assert len(calls) == 1
    assert calls[0]['index_method'] == 'paasche'


def test_store_index_passes_selected_index_method_to_service(
    qtbot, analytics_widget, few_stores, monkeypatch
):
    calls = []

    def fake_store_index(**kwargs):
        calls.append(kwargs)
        return {'points': [], 'kpi': None}

    monkeypatch.setattr(
        'app.service.analytics.store_inflation_index', fake_store_index
    )

    _select_store(analytics_widget, few_stores[0].id)
    analytics_widget.index_method_combo.setCurrentIndex(
        analytics_widget.index_method_combo.findData('fisher')
    )

    analytics_widget.build()

    qtbot.waitUntil(
        lambda: analytics_widget.btn_build.isEnabled(), timeout=2000
    )
    assert len(calls) == 1
    assert calls[0]['index_method'] == 'fisher'


def test_product_index_does_not_pass_index_method_to_service(
    qtbot, analytics_widget, product_vegetable, monkeypatch
):
    """product_inflation_index не принимает index_method — и не должен.

    У одного товара взвешивать нечем: Ласпейрес/Пааше/Фишер дают одно и
    то же число, так что параметр там был бы декоративным.
    """
    calls = []

    def fake_product_index(**kwargs):
        calls.append(kwargs)
        return {'points': [], 'kpi': None}

    monkeypatch.setattr(
        'app.service.analytics.product_inflation_index',
        fake_product_index,
    )

    _select_product(analytics_widget, product_vegetable.id)
    analytics_widget.build()

    qtbot.waitUntil(
        lambda: analytics_widget.btn_build.isEnabled(), timeout=2000
    )
    assert len(calls) == 1
    assert 'index_method' not in calls[0]


# ---------- basket_index (пользовательская корзина) ----------

def test_basket_index_enables_product_ids_and_index_method(
    analytics_widget,
):
    _select_basket(analytics_widget)

    assert analytics_widget.product_picker.isEnabled() is True
    assert analytics_widget.index_method_combo.isEnabled() is True
    assert analytics_widget.product_combo.isEnabled() is False
    assert analytics_widget.category_combo.isEnabled() is False
    assert analytics_widget.store_combo.isEnabled() is False


def test_basket_index_requires_at_least_one_product_id(
    analytics_widget, information_calls, monkeypatch,
):
    def fail_if_called(**kwargs):
        raise AssertionError(
            'basket_inflation_index не должен вызываться без товаров'
        )

    monkeypatch.setattr(
        'app.service.analytics.basket_inflation_index', fail_if_called,
    )

    _select_basket(analytics_widget)
    analytics_widget.build()

    assert information_calls, 'ожидали подсказку про пустую корзину'
    assert analytics_widget.btn_build.isEnabled() is True


def test_basket_index_passes_product_ids_and_method_to_service(
    qtbot, analytics_widget, few_products, monkeypatch,
):
    calls = []

    def fake_basket_index(**kwargs):
        calls.append(kwargs)
        return {'points': [], 'kpi': None}

    monkeypatch.setattr(
        'app.service.analytics.basket_inflation_index',
        fake_basket_index,
    )

    _select_basket(analytics_widget, [p.id for p in few_products])
    analytics_widget.index_method_combo.setCurrentIndex(
        analytics_widget.index_method_combo.findData('paasche')
    )

    analytics_widget.build()

    qtbot.waitUntil(
        lambda: analytics_widget.btn_build.isEnabled(), timeout=2000
    )
    assert len(calls) == 1
    assert set(calls[0]['product_ids']) == {p.id for p in few_products}
    assert calls[0]['index_method'] == 'paasche'


def test_store_index_plot_title_uses_real_title_not_hardcoded_string(
    qtbot, analytics_widget, few_stores, product_vegetable,
):
    """Регрессия: title считался через _build_plot_title(), но в
    _plot_index() подставлялась захардкоженная строка 'Индекс по
    магазину (база=100)', а не он. Из-за этого название магазина и
    выбранный метод индекса никогда не попадали в заголовок графика.

    Нужна хотя бы одна реальная покупка: при пустом результате
    _plot_index() выходит раньше set_title(), и тест ничего бы не
    проверял, падая по не той причине.
    """
    purchases.create_purchase(
        store_id=few_stores[0].id, product_id=product_vegetable.id,
        quantity=1.0, price=100.0, purchase_date=date(2024, 1, 10),
    )

    _select_store(analytics_widget, few_stores[0].id)

    analytics_widget.build()

    qtbot.waitUntil(
        lambda: analytics_widget.btn_build.isEnabled(), timeout=2000
    )
    assert few_stores[0].name in analytics_widget.ax.get_title()


def test_build_button_is_enlarged_and_bold(analytics_widget):
    """Кнопка «Построить» должна бросаться в глаза — крупнее и жирнее
    дефолтной, раз она теперь главное действие в левой панели, а не
    одна из двух кнопок в верхней строке."""
    assert analytics_widget.btn_build.minimumHeight() >= 44
    assert analytics_widget.btn_build.font().bold() is True

