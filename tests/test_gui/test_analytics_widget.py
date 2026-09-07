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

import pytest
from app.gui.analytics import AnalyticsWidget


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
