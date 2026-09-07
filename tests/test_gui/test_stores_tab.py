"""GUI-тесты для StoresTab (app/gui/tabs/stores.py).

Новая техника по сравнению с PurchaseDialog:
on_add()/on_edit() внутри себя вызывают dlg.exec() — это реальный
модальный цикл, который в headless-тесте никто не закроет кликом.
Раньше мы обходили это, вызывая _on_ok() напрямую. Здесь так не
получится, потому что сам диалог создаётся *внутри* on_add()/on_edit(),
а не снаружи. Поэтому подменяем два места разом:

1. make_add_dialog()/make_edit_dialog() — на фейк, который создаёт
   диалог и сразу заполняет поля (как будто пользователь уже напечатал).
2. QDialog.exec — глобально на лямбду, которая просто возвращает
   Accepted, не открывая никакого окна и не блокируя поток.

После этого on_add()/on_edit() отрабатывают как обычный синхронный
код: создали диалог -> "нажали ОК" -> прочитали values() -> сходили
в CRUD.
"""


from app.gui.tabs.common import NameDescDialog
from app.gui.tabs.stores import StoresTab


def _row_names(tab: StoresTab) -> list[str]:
    return [tab.model.row_dict(i)['name'] for i in range(tab.model.rowCount())]


# ---------- on_add ----------

def test_on_add_creates_store(qtbot, accept_dialogs, monkeypatch):
    tab = StoresTab()
    qtbot.addWidget(tab)

    def fake_make_add_dialog(self):
        dlg = NameDescDialog(self, title='Магазин')
        dlg.name_edit.setText('Ашан')
        dlg.desc_edit.setPlainText('Гипермаркет')
        return dlg

    monkeypatch.setattr(StoresTab, 'make_add_dialog', fake_make_add_dialog)

    tab.on_add()

    assert 'Ашан' in _row_names(tab)


def test_on_edit_updates_store(
    qtbot,
    accept_dialogs,
    monkeypatch,
    single_store,
):
    tab = StoresTab()
    qtbot.addWidget(tab)
    tab.table.setCurrentIndex(tab.table.model().index(0, 0))

    def fake_make_edit_dialog(self, row):
        dlg = NameDescDialog(
            self,
            title='Магазин',
            name=row.get('name') or '',
            description=row.get('description') or '',
        )
        dlg.name_edit.setText('Магнит Косметик')
        return dlg

    monkeypatch.setattr(StoresTab, 'make_edit_dialog', fake_make_edit_dialog)

    tab.on_edit()

    assert _row_names(tab) == ['Магнит Косметик']


def test_on_delete_confirmed_removes_store(
    qtbot,
    confirm_dialog,
    single_store,
):
    tab = StoresTab()
    qtbot.addWidget(tab)
    tab.table.setCurrentIndex(tab.table.model().index(0, 0))

    confirm_dialog(True)
    tab.on_delete()

    assert tab.model.rowCount() == 0


def test_on_delete_cancelled_keeps_store(qtbot, confirm_dialog, single_store):
    tab = StoresTab()
    qtbot.addWidget(tab)
    tab.table.setCurrentIndex(tab.table.model().index(0, 0))

    confirm_dialog(False)
    tab.on_delete()

    assert tab.model.rowCount() == 1


def test_on_delete_blocked_when_store_has_purchases(
    qtbot,
    confirm_dialog,
    warning_calls,
    single_store,
    few_purchase_in_single_store
):
    tab = StoresTab()
    qtbot.addWidget(tab)
    tab.table.setCurrentIndex(tab.table.model().index(0, 0))

    confirm_dialog(True)
    tab.on_delete()

    assert tab.model.rowCount() == 1
    assert warning_calls, 'ожидали предупреждение "Нельзя удалить"'
