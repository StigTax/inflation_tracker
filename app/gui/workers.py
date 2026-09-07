"""Универсальный воркер для тяжёлых вызовов вне GUI-потока.

Идея: не городить отдельный QThread-класс под каждый тяжёлый расчёт
(аналитика сегодня, что-то ещё завтра), а иметь один переиспользуемый
worker, которому просто скармливаешь функцию и аргументы.

Как это работает с точки зрения потоков:
- CallableWorker живёт в фоновом QThread и просто дёргает fn(*args,
  **kwargs) — никаких Qt-виджетов внутри run() трогать нельзя, только
  чистые вычисления/поход в БД.
- finished/failed — сигналы. Qt сам организует безопасную передачу
  данных обратно в основной поток (queued connection), когда слот
  подключён к объекту, живущему в другом потоке. Поэтому GUI может
  спокойно обновлять виджеты в слоте, подключённом к finished/failed —
  этот код физически выполнится в основном потоке, а не в фоновом.
"""

from __future__ import annotations

from typing import Any, Callable

from PyQt6.QtCore import QObject, QThread, pyqtSignal


class CallableWorker(QObject):
    """Выполняет fn(*args, **kwargs) в текущем (предполагается — фоновом)
    потоке и оповещает о результате через сигналы.
    """

    finished = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, fn: Callable[..., Any], *args: Any, **kwargs: Any):
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    def run(self) -> None:
        try:
            result = self._fn(*self._args, **self._kwargs)
        except Exception as e:  # noqa: BLE001
            # Любое исключение из fn прокидываем в GUI как текст, а не
            # роняем поток молча — иначе пользователь просто увидит,
            # что "Построить" тихо ничего не сделало.
            self.failed.emit(str(e))
            return
        self.finished.emit(result)


class BackgroundTaskRunner:
    """Прячет бойлерплейт QThread/CallableWorker за одним методом .run().

    Гарантирует:
    - нельзя запустить вторую задачу поверх ещё не завершённой —
      иначе не определено, чей результат прилетит первым, и можно
      словить гонку на виджетах, которые оба колбэка пытаются менять;
    - на успех/ошибку/всегда вызываются свои колбэки в основном потоке;
    - QThread и worker не собираются GC, пока поток жив (классическая
      PyQt-беда "QThread: Destroyed while thread is still running"
      случается именно из-за отсутствия удерживаемой ссылки).
    """

    def __init__(self) -> None:
        self._thread: QThread | None = None
        self._worker: CallableWorker | None = None

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.isRunning()

    def run(
        self,
        fn: Callable[..., Any],
        *,
        on_success: Callable[[Any], None],
        on_error: Callable[[str], None],
        on_finished: Callable[[], None] | None = None,
        **kwargs: Any,
    ) -> bool:
        """Запускает fn(**kwargs) в фоновом потоке.

        Returns:
            bool: True, если задача запущена. False, если предыдущая
            ещё выполняется и новую пришлось проигнорировать.
        """
        if self.is_running():
            return False

        thread = QThread()
        worker = CallableWorker(fn, **kwargs)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(on_success)
        worker.failed.connect(on_error)

        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        # Обнуляем ссылки сразу, как только поток завершился — не
        # дожидаясь, пока Qt реально соберёт объекты по deleteLater().
        # Иначе есть шанс, что is_running()/shutdown() обратятся к
        # self._thread уже ПОСЛЕ того, как event loop успел удалить
        # C++-объект, и словят RuntimeError на "мёртвой" обёртке.
        thread.finished.connect(self._clear_refs)
        if on_finished is not None:
            thread.finished.connect(on_finished)

        self._thread = thread
        self._worker = worker
        thread.start()
        return True

    def _clear_refs(self) -> None:
        self._thread = None
        self._worker = None

    def shutdown(self) -> None:
        """Дожидается завершения фонового потока перед закрытием окна.

        Без этого можно словить "QThread: Destroyed while thread is
        still running" при закрытии приложения посреди расчёта.
        """
        if self.is_running():
            self._thread.quit()
            self._thread.wait()