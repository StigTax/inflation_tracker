"""Тесты на BackgroundTaskRunner (app/gui/workers.py).

Ключевая техника: сигналы finished/failed доставляются через queued
connection, а значит физически долетают до слота только когда крутится
цикл событий Qt. qtbot.waitUntil(...) как раз это и делает — крутит
event loop, пока condition() не станет True (или не истечёт timeout).
Обычный time.sleep() тут не поможет: без активного event loop сигнал
из фонового потока просто зависнет в очереди и никогда не будет
доставлен в слот основного потока.
"""

import threading

import pytest
from app.gui.workers import BackgroundTaskRunner


@pytest.fixture
def runner():
    return BackgroundTaskRunner()


def test_run_calls_on_success_with_result(qtbot, runner):
    """Успешный вызов долетает до on_success с результатом fn(**kwargs)."""
    captured = {}

    started = runner.run(
        lambda a, b: a + b,
        on_success=lambda res: captured.setdefault('result', res),
        on_error=lambda msg: captured.setdefault('error', msg),
        a=2,
        b=3,
    )

    assert started is True
    qtbot.waitUntil(lambda: 'result' in captured, timeout=2000)
    assert captured['result'] == 5
    assert 'error' not in captured


def test_run_calls_on_error_when_fn_raises(qtbot, runner):
    """Исключение внутри fn долетает до on_error текстом, а не роняет поток."""
    captured = {}

    def boom():
        raise ValueError('что-то пошло не так')

    runner.run(
        boom,
        on_success=lambda res: captured.setdefault('result', res),
        on_error=lambda msg: captured.setdefault('error', msg),
    )

    qtbot.waitUntil(lambda: 'error' in captured, timeout=2000)
    assert 'result' not in captured
    assert 'что-то пошло не так' in captured['error']


def test_run_returns_false_while_busy(qtbot, runner):
    """Нельзя запустить вторую задачу поверх ещё не завершённой.

    threading.Event — не для красоты: без явной синхронизации первая
    задача (даже "медленная" по нашим меркам) может успеть завершиться
    ДО того, как мы попытаемся запустить вторую, и тест будет то падать,
    то проходить в зависимости от скорости машины. Event гарантирует,
    что вторая run() случится строго пока первая ещё не отпущена.
    """
    release = threading.Event()
    captured = []

    def slow():
        release.wait(timeout=2)
        return 'first'

    first_started = runner.run(
        slow,
        on_success=captured.append,
        on_error=captured.append,
    )
    second_started = runner.run(
        lambda: 'second',
        on_success=captured.append,
        on_error=captured.append,
    )

    release.set()
    qtbot.waitUntil(lambda: bool(captured), timeout=2000)

    assert first_started is True
    assert second_started is False
    assert captured == ['first']


def test_can_start_new_task_after_previous_finished(qtbot, runner):
    """После завершения задачи ссылки очищены — новую можно стартовать.

    Косвенно проверяет _clear_refs(): если бы self._thread/self._worker
    оставались висеть на уже мёртвых объектах, is_running() внутри
    следующего run() мог бы либо соврать, либо упасть с RuntimeError
    на удалённом C++-объекте.
    """
    captured = []

    runner.run(
        lambda: 'first',
        on_success=captured.append,
        on_error=captured.append,
    )
    qtbot.waitUntil(lambda: bool(captured), timeout=2000)

    started_again = runner.run(
        lambda: 'second',
        on_success=captured.append,
        on_error=captured.append,
    )

    assert started_again is True
    qtbot.waitUntil(lambda: len(captured) == 2, timeout=2000)
    assert captured == ['first', 'second']


def test_shutdown_waits_for_running_task(qtbot, runner):
    """shutdown() блокируется до завершения фоновой задачи, не падает.

    Это ровно тот сценарий, который защищает MainWindow.closeEvent —
    закрытие приложения посреди расчёта не должно ронять процесс.
    """
    release = threading.Event()
    captured = []

    def slow():
        release.wait(timeout=2)
        return 'done'

    runner.run(slow, on_success=captured.append, on_error=captured.append)

    release.set()
    runner.shutdown()

    assert runner.is_running() is False
