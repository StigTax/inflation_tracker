"""Общие фикстуры для GUI-тестов (только tests/test_gui/*).

Вынесены отдельно от корневого conftest.py, чтобы CLI- и
service-тесты не тянули за собой PyQt6 — им он не нужен.
"""

import pytest
from app.gui.tabs.purchases import PurchaseDialog
from PyQt6.QtWidgets import QDialog, QMessageBox


@pytest.fixture
def accept_dialogs(monkeypatch):
    """Подменяет QDialog.exec(), чтобы модалки не блокировали тест.

    Нужен там, где сам диалог создаётся внутри тестируемого кода
    (on_add()/on_edit() у CRUD-вкладок) — доступа к инстансу диалога
    до вызова exec() у теста нет, поэтому патчим на уровне класса.
    """
    monkeypatch.setattr(
        QDialog, 'exec', lambda self: QDialog.DialogCode.Accepted
    )


@pytest.fixture
def confirm_dialog(monkeypatch):
    """Фабрика для подмены QMessageBox.question().

    Использование в тесте:
        confirm_dialog(True)   # пользователь нажал "Да"
        confirm_dialog(False)  # "Нет" / закрыл окно
    """

    def _set(answer: bool):
        button = (
            QMessageBox.StandardButton.Yes
            if answer
            else QMessageBox.StandardButton.No
        )
        monkeypatch.setattr(
            QMessageBox, 'question', staticmethod(lambda *a, **kw: button)
        )

    return _set


@pytest.fixture
def warning_calls(monkeypatch):
    """Перехватывает QMessageBox.warning(), отдаёт список вызовов.

    Годится и для валидации форм (пустое поле), и для guard'ов
    безопасного удаления — везде, где код на ошибку показывает
    предупреждение, а не падает молча.
    """
    calls = []
    monkeypatch.setattr(
        QMessageBox, 'warning',
        staticmethod(lambda *a, **kw: calls.append(a)),
    )
    return calls


@pytest.fixture
def empty_dialog(qtbot, product_vegetable, few_stores):
    """Диалог без предзаполненных продукта/магазина (дефолтное состояние)."""
    dlg = PurchaseDialog()
    qtbot.addWidget(dlg)  # обязательно: без этого Qt не подчистит виджет
    return dlg


@pytest.fixture
def filled_dialog(qtbot, product_vegetable, few_stores):
    """Диалог с уже выбранными продуктом, магазином, кол-вом и суммой."""
    dlg = PurchaseDialog(
        product_id=product_vegetable.id,
        store_id=few_stores[0].id,
        quantity=2.0,
        total_price=150.0,
    )
    qtbot.addWidget(dlg)
    return dlg

@pytest.fixture
def critical_calls(monkeypatch):
    """Перехватывает QMessageBox.critical(), отдаёт список вызовов.

    Нужен там, где ошибка не блокирует форму (как warning), а сообщает
    о сбое операции — например, падение фонового расчёта аналитики.
    """
    calls = []
    monkeypatch.setattr(
        QMessageBox, 'critical',
        staticmethod(lambda *a, **kw: calls.append(a)),
    )
    return calls

@pytest.fixture
def information_calls(monkeypatch):
    """Перехватывает QMessageBox.information(), отдаёт список вызовов.

    Для нейтральных подсказок вроде "выбери строку в таблице" или
    "добавь хотя бы одну строку" — это не ошибка и не предупреждение
    о невалидности, просто мягкая подсказка пользователю.
    """
    calls = []
    monkeypatch.setattr(
        QMessageBox, 'information',
        staticmethod(lambda *a, **kw: calls.append(a)),
    )
    return calls
