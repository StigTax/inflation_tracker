from __future__ import annotations

from datetime import date
from typing import Optional

import matplotlib.dates as mdates
import pandas as pd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QGuiApplication, QPalette
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from app.crud import category_crud, product_crud, store_crud
from app.gui.data_manager import DataManagerDialog
from app.gui.qt_helpers import setup_searchable_combo
from app.gui.ref_cache import get_cached
from app.gui.workers import BackgroundTaskRunner
from app.service import analytics as svc
from app.service.crud_service import list_items
from app.service.purchases import (
    get_purchase_date_bounds,
    get_purchase_usage_counts,
)

_GROUP_FREQ = {
    'День': 'day',
    'Неделя': 'week',
    'Месяц': 'month',
    'Год': 'year',
}

# Насколько большим должен быть разрыв между соседними точками (в днях),
# чтобы график перестал соединять их линией. Идея: если между покупками
# прошло, скажем, три месяца при дневной группировке, прямая линия между
# ними — чистый домысел matplotlib, а не реальный тренд. Эвристика,
# можно подстроить под свои привычки покупок.
_GAP_BREAK_DAYS = {
    'day': 21,
    'week': 45,
    'month': 95,
    'year': 550,
}

# Подписывать цену над точками только пока их немного — иначе подписи
# налезают друг на друга и превращают график в кашу. При дневной
# группировке за год это могут быть сотни точек.
_MAX_ANNOTATED_POINTS = 15

_LIGHT_COLORS = {
    'figure_bg': '#ffffff',
    'axes_bg': '#ffffff',
    'text': '#1a1a1a',
    'grid': '#cfcfcf',
    'line': '#1f77b4',
    'baseline': '#7a7a7a',
}

_DARK_COLORS = {
    'figure_bg': '#232629',
    'axes_bg': '#232629',
    'text': '#e6e6e6',
    'grid': '#4a4d50',
    'line': '#5fa8ff',
    'baseline': '#9a9da0',
}


def _is_dark_mode() -> bool:
    """Определяет, активна ли сейчас тёмная системная тема.

    Основной способ — QGuiApplication.styleHints().colorScheme()
    (доступно с Qt 6.5): читает системную настройку темы напрямую,
    без всякого угадывания. Фолбэк — светлота цвета окна из текущей
    палитры приложения; срабатывает, если платформа/версия Qt почему-то
    вернула Unknown вместо реальной схемы.
    """
    try:
        scheme = QGuiApplication.styleHints().colorScheme()
        if scheme == Qt.ColorScheme.Dark:
            return True
        if scheme == Qt.ColorScheme.Light:
            return False
    except Exception:
        pass

    app = QApplication.instance()
    if app is None:
        return False
    window_color = app.palette().color(QPalette.ColorRole.Window)
    return window_color.lightness() < 128


class AnalyticsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._data_min: Optional[date] = None
        self._data_max: Optional[date] = None
        self._task_runner = BackgroundTaskRunner()

        # --- Верхняя панель (кнопки) ---
        self.btn_data = QPushButton('Данные…')
        self.btn_build = QPushButton('Построить')

        self.btn_data.clicked.connect(self.open_data_manager)
        self.btn_build.clicked.connect(self.build)

        top = QHBoxLayout()
        top.addWidget(self.btn_data)
        top.addStretch(1)
        top.addWidget(self.btn_build)

        # --- Левая панель параметров ---
        self.kind_combo = QComboBox()
        self.kind_combo.addItem('Продукт: индекс', 'product_index')
        self.kind_combo.addItem('Категория: индекс', 'category_index')
        self.kind_combo.addItem('Магазин: индекс', 'store_index')

        self.product_combo = QComboBox()
        self.category_combo = QComboBox()
        self.store_combo = QComboBox()

        setup_searchable_combo(
            self.product_combo,
            placeholder='Начни печатать продукт…'
        )
        setup_searchable_combo(
            self.category_combo,
            placeholder='Начни печатать категорию…'
        )
        setup_searchable_combo(
            self.store_combo,
            placeholder='Начни печатать магазин…'
        )

        self.product_ids_edit = QLineEdit()
        self.product_ids_edit.setPlaceholderText(
            'ID продуктов через запятую (пусто — все)'
        )

        self.use_dates = QCheckBox('Фильтр по датам')
        self.date_from = QDateEdit()
        self.date_to = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_to.setCalendarPopup(True)
        self.date_from.setEnabled(False)
        self.date_to.setEnabled(False)
        self.use_dates.stateChanged.connect(self._toggle_dates)

        self.group_combo = QComboBox()
        for k, v in _GROUP_FREQ.items():
            self.group_combo.addItem(k, v)

        self.price_mode = QComboBox()
        self.price_mode.addItem('Как заплатил (paid)', 'paid')
        self.price_mode.addItem('Обычная цена (regular)', 'regular')

        self.promo_mode = QComboBox()
        self.promo_mode.addItem('Включая акции', 'include')
        self.promo_mode.addItem('Без акций', 'exclude')
        self.promo_mode.addItem('Только акции', 'only')

        self.index_method_combo = QComboBox()
        self.index_method_combo.addItem('Ласпейрес', 'laspeyres')
        self.index_method_combo.addItem('Пааше', 'paasche')
        self.index_method_combo.addItem('Фишер', 'fisher')

        self.kind_combo.currentIndexChanged.connect(self._on_kind_changed)

        left_form = QFormLayout()
        left_form.addRow('Тип:', self.kind_combo)
        left_form.addRow('Продукт:', self.product_combo)
        left_form.addRow('Категория:', self.category_combo)
        left_form.addRow('Магазин:', self.store_combo)
        left_form.addRow('Корзина (ID прод.):', self.product_ids_edit)
        left_form.addRow('Метод индекса:', self.index_method_combo)

        left_form.addRow('', self.use_dates)
        left_form.addRow('с:', self.date_from)
        left_form.addRow('по:', self.date_to)
        left_form.addRow('Группировка:', self.group_combo)
        left_form.addRow('Режим цены:', self.price_mode)
        left_form.addRow('Акции:', self.promo_mode)

        left = QWidget()
        left.setLayout(left_form)
        left.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding
        )
        left.setMaximumWidth(520)

        # --- Правая панель (график + метрики) ---
        self.figure = Figure(figsize=(6, 4))
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        self._theme = _LIGHT_COLORS
        self._apply_theme()

        self.kpi = QLabel('Выбери параметры и нажми «Построить».')
        self.kpi.setWordWrap(True)

        right = QVBoxLayout()
        right.addWidget(self.canvas, stretch=1)
        right.addWidget(self.kpi, stretch=0)

        right_w = QWidget()
        right_w.setLayout(right)
        right_w.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        splitter = QSplitter()
        splitter.addWidget(left)
        splitter.addWidget(right_w)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)

        splitter.setSizes([360, 900])

        root = QVBoxLayout()
        root.addLayout(top)
        root.addWidget(splitter, stretch=1)
        self.setLayout(root)

        self._reload_combos()
        self._init_date_bounds()
        self._on_kind_changed()

    # ------------------- date bounds -------------------

    def _toggle_dates(self) -> None:
        """Включает/выключает фильтр по датам и выставляет разумные значения.

        Если фильтр включён и в БД есть покупки, диапазон в UI
        устанавливается на полный доступный интервал.
        """
        enabled = self.use_dates.isChecked()
        self.date_from.setEnabled(enabled)
        self.date_to.setEnabled(enabled)

        if enabled and self._data_min and self._data_max:
            self._set_date_edits(self._data_min, self._data_max)

    def _init_date_bounds(self) -> None:
        """Инициализирует допустимые границы дат по данным из БД.

        Берёт min/max по покупкам и устанавливает:
        - minimum/maximum для QDateEdit
        - текущие значения полей даты.
        """
        dmin, dmax = get_purchase_date_bounds()
        self._data_min = dmin
        self._data_max = dmax

        if dmin and dmax:
            qmin = QDate(dmin.year, dmin.month, dmin.day)
            qmax = QDate(dmax.year, dmax.month, dmax.day)
            self.date_from.setMinimumDate(qmin)
            self.date_from.setMaximumDate(qmax)
            self.date_to.setMinimumDate(qmin)
            self.date_to.setMaximumDate(qmax)
            self._set_date_edits(dmin, dmax)
            return

        today = date.today()
        qt = QDate(today.year, today.month, today.day)
        self.date_from.setDate(qt)
        self.date_to.setDate(qt)

    def _set_date_edits(self, dmin: date, dmax: date) -> None:
        """Устанавливает значения QDateEdit.

        Args:
            dmin: Минимальная дата.
            dmax: Максимальная дата.
        """
        self.date_from.setDate(QDate(dmin.year, dmin.month, dmin.day))
        self.date_to.setDate(QDate(dmax.year, dmax.month, dmax.day))

    # ------------------- reload combos with counts -------------------

    def _reload_combos(self) -> None:
        """Обновляет продукты/категории/магазины одним проходом.

        get_purchase_usage_counts() — это 3 GROUP BY по всей таблице
        покупок; незачем гонять его трижды ради одних и тех же чисел.
        """
        counts = get_purchase_usage_counts()
        self.reload_products(counts)
        self.reload_categories(counts)
        self.reload_stores(counts)

    def reload_products(self, counts: Optional[dict] = None) -> None:
        """Перезагружает список продуктов и добавляет счётчик покупок."""
        self.product_combo.clear()
        self.product_combo.addItem('— выбери продукт —', None)

        prod_cnt = (counts or get_purchase_usage_counts()).get('products', {})

        products = get_cached(
            'products', lambda: list_items(product_crud, limit=5000)
        )
        for p in products:
            unit = ''
            if getattr(p, 'unit', None):
                unit = f'{p.unit.measure_type} {p.unit.unit}'
            cnt = int(prod_cnt.get(p.id, 0))
            self.product_combo.addItem(f'{p.name} ({unit}) — {cnt}', p.id)

    def reload_categories(self, counts: Optional[dict] = None) -> None:
        """Перезагружает список категорий и добавляет счётчик покупок."""
        self.category_combo.clear()
        self.category_combo.addItem('— выбери категорию —', None)

        cat_cnt = (counts or get_purchase_usage_counts()).get('categories', {})

        cats = get_cached(
            'categories', lambda: list_items(category_crud, limit=5000)
        )
        for c in cats:
            cnt = int(cat_cnt.get(c.id, 0))
            self.category_combo.addItem(f'{c.name} — {cnt}', c.id)

    def reload_stores(self, counts: Optional[dict] = None) -> None:
        """Перезагружает список магазинов и добавляет счётчик покупок."""
        self.store_combo.clear()
        self.store_combo.addItem('— выбери магазин —', None)

        store_cnt = (counts or get_purchase_usage_counts()).get('stores', {})

        stores = get_cached(
            'stores', lambda: list_items(store_crud, limit=5000)
        )
        for s in stores:
            cnt = int(store_cnt.get(s.id, 0))
            self.store_combo.addItem(f'{s.name} — {cnt}', s.id)

    def open_data_manager(self) -> None:
        """Открывает диалог управления данными и обновляет списки."""
        dlg = DataManagerDialog(self)
        dlg.exec()
        self._reload_combos()
        self._init_date_bounds()

    # ------------------- kind switching -------------------

    def _on_kind_changed(self) -> None:
        """Реакция на смену типа аналитики.

        Делает три вещи:
        1) включает/выключает нужные поля
        2) сбрасывает неиспользуемые поля на дефолтные значения
        3) сбрасывает фильтр дат при смене режима
        """
        kind = self.kind_combo.currentData()

        need_product = kind == 'product_index'
        need_category = kind == 'category_index'
        need_store = kind == 'store_index'
        # Метод индекса (Ласпейрес/Пааше/Фишер) имеет смысл только там,
        # где в корзине больше одного товара — у product_index веса не
        # на чем считать, там все три метода дают одно и то же число.
        need_index_method = need_category or need_store

        self.product_combo.setEnabled(need_product)
        self.category_combo.setEnabled(need_category)
        self.store_combo.setEnabled(need_store)
        self.product_ids_edit.setEnabled(need_store)
        self.index_method_combo.setEnabled(need_index_method)

        if not need_product:
            self.product_combo.setCurrentIndex(0)
        if not need_category:
            self.category_combo.setCurrentIndex(0)
        if not need_store:
            self.store_combo.setCurrentIndex(0)
            self.product_ids_edit.clear()
        if not need_index_method:
            self.index_method_combo.setCurrentIndex(0)

        self._toggle_dates()

        self.group_combo.setEnabled(True)

    def _set_group_by(self, value: str) -> None:
        """Выставляет group_by в combo по itemData.

        Args:
            value: Одно из 'day'/'week'/'month'/'year'.
        """
        for i in range(self.group_combo.count()):
            if self.group_combo.itemData(i) == value:
                self.group_combo.setCurrentIndex(i)
                return

    def _parse_ids(self) -> Optional[list[int]]:
        """Парсит список id продуктов из текстового поля.

        Returns:
            Список id, если поле заполнено, иначе None.

        Raises:
            ValueError: Если найден некорректный id.
        """
        raw = (self.product_ids_edit.text() or '').strip()
        if not raw:
            return None
        parts = [p.strip() for p in raw.split(',') if p.strip()]
        ids: list[int] = []
        for p in parts:
            if not p.isdigit():
                raise ValueError(f'Некорректный id: {p}')
            ids.append(int(p))
        return ids or None

    def _clean_product_label(self, product_id: int) -> str:
        """Имя продукта для заголовка графика, без счётчика "— N покупок".

        currentText() комбобокса для этого не годится: там формат
        "Название (ед.) — N", где N — число покупок для UI-подсказки в
        выпадающем списке. В заголовке графика это "— N" выглядит как
        часть названия товара, а не как метаинформация.
        """
        for p in get_cached(
            'products', lambda: list_items(product_crud, limit=5000)
        ):
            if p.id == product_id:
                unit = (
                    f'{p.unit.measure_type} {p.unit.unit}'
                    if getattr(p, 'unit', None) else ''
                )
                return f'{p.name} ({unit})' if unit else p.name
        return 'Продукт'

    def _clean_category_label(self, category_id: int) -> str:
        """Имя категории для заголовка графика, без счётчика покупок."""
        for c in get_cached(
            'categories', lambda: list_items(category_crud, limit=5000)
        ):
            if c.id == category_id:
                return c.name
        return 'Категория'

    def _clean_store_label(self, store_id: int) -> str:
        """Имя магазина для заголовка графика, без счётчика покупок."""
        for s in get_cached(
            'stores', lambda: list_items(store_crud, limit=5000)
        ):
            if s.id == store_id:
                return s.name
        return 'Магазин'

    # ------------------- build + plots -------------------

    def build(self) -> None:
        """Собирает параметры, вызывает аналитику и отрисовывает график."""
        kind = self.kind_combo.currentData()
        if not kind:
            QMessageBox.information(self, 'Ок', 'Выбери тип аналитики.')
            return

        from_date: Optional[date] = None
        to_date: Optional[date] = None
        if self.use_dates.isChecked():
            from_date = self.date_from.date().toPyDate()
            to_date = self.date_to.date().toPyDate()
            if from_date and to_date and from_date > to_date:
                QMessageBox.information(
                    self,
                    'Ок',
                    'Дата \'с\' не может быть позже даты \'по\'.'
                )
                return

        group_by = self.group_combo.currentData() or 'month'
        price_mode = self.price_mode.currentData() or 'paid'
        promo_mode = self.promo_mode.currentData() or 'include'
        index_method = self.index_method_combo.currentData() or 'laspeyres'

        product_ids = None
        if kind == 'store_index':
            try:
                product_ids = self._parse_ids()
            except ValueError as e:
                QMessageBox.information(self, 'Ошибка', str(e))
                return

        try:
            if kind == 'product_index':
                product_id = self.product_combo.currentData()
                if product_id is None:
                    QMessageBox.information(
                        self,
                        'Ок',
                        'Сначала выбери продукт.'
                    )
                    return
                obj_name = self._clean_product_label(int(product_id))
                title = self._build_plot_title(
                    kind=kind,
                    obj_name=obj_name,
                    group_by=group_by,
                    price_mode=price_mode,
                    promo_mode=promo_mode,
                    from_date=from_date,
                    to_date=to_date,
                )

                self._run_analytics(
                    svc.product_inflation_index,
                    on_success=lambda res: self._plot_index(
                        res, title=title, group_by=group_by,
                    ),
                    product_id=int(product_id),
                    from_date=from_date,
                    to_date=to_date,
                    group_by=group_by,
                    price_mode=price_mode,
                    promo_mode=promo_mode,
                )
                return

            if kind == 'category_index':
                category_id = self.category_combo.currentData()
                if category_id is None:
                    QMessageBox.information(
                        self,
                        'Ок',
                        'Сначала выбери категорию.'
                    )
                    return
                obj_name = self._clean_category_label(int(category_id))
                title = self._build_plot_title(
                    kind=kind,
                    obj_name=obj_name,
                    group_by=group_by,
                    price_mode=price_mode,
                    promo_mode=promo_mode,
                    from_date=from_date,
                    to_date=to_date,
                    index_method=index_method,
                )
                self._run_analytics(
                    svc.category_inflation_index,
                    on_success=lambda res: self._plot_index(
                        res, title=title, group_by=group_by,
                    ),
                    category_id=int(category_id),
                    from_date=from_date,
                    to_date=to_date,
                    group_by=group_by,
                    price_mode=price_mode,
                    promo_mode=promo_mode,
                    index_method=index_method,
                )
                return

            if kind == 'store_index':
                store_id = self.store_combo.currentData()
                if store_id is None:
                    QMessageBox.information(
                        self,
                        'Ок',
                        'Сначала выбери магазин.'
                    )
                    return
                obj_name = self._clean_store_label(int(store_id))
                title = self._build_plot_title(
                    kind=kind,
                    obj_name=obj_name,
                    group_by=group_by,
                    price_mode=price_mode,
                    promo_mode=promo_mode,
                    from_date=from_date,
                    to_date=to_date,
                    index_method=index_method,
                )
                self._run_analytics(
                    svc.store_inflation_index,
                    on_success=lambda res: self._plot_index(
                        res,
                        title=title,
                        group_by=group_by,
                    ),
                    store_id=int(store_id),
                    from_date=from_date,
                    to_date=to_date,
                    product_ids=product_ids,
                    group_by=group_by,
                    price_mode=price_mode,
                    promo_mode=promo_mode,
                    index_method=index_method,
                )
                return

            QMessageBox.information(
                self,
                'Ок',
                f'Неизвестный тип аналитики: {kind}'
            )
            return

        except Exception as e:
            self._reset_axes()
            self.canvas.draw_idle()
            self.kpi.setText('Ошибка при построении.')
            QMessageBox.critical(self, 'Ошибка', str(e))
            return

    def _run_analytics(self, fn, *, on_success, **kwargs) -> None:
        """Запускает тяжёлый расчёт аналитики в фоне, не блокируя UI.

        Пока расчёт идёт, кнопка "Построить" недоступна — это не
        только UX (видно, что программа работает, а не зависла), но и
        защита от гонки: если бы два расчёта одновременно писали в
        один и тот же self.figure/self.canvas, порядок отрисовки был
        бы непредсказуем.
        """
        if self._task_runner.is_running():
            # Уже что-то считается — новый клик поверх молча игнорируем,
            # не трогая текущее busy-состояние. Раньше здесь по ветке
            # "не удалось запустить" ошибочно вызывался _set_busy(False),
            # что снимало disable с кнопки, пока реальный расчёт ещё шёл.
            return

        self._set_busy(True)
        self._task_runner.run(
            fn,
            on_success=on_success,
            on_error=self._on_build_failed,
            on_finished=lambda: self._set_busy(False),
            **kwargs,
        )

    def _on_build_failed(self, message: str) -> None:
        """Слот failed — вызывается в основном потоке (Qt queued connection).

        Здесь можно безопасно трогать self.canvas/self.kpi, даже
        несмотря на то, что расчёт упал в фоновом потоке.
        """
        self._reset_axes()
        self.canvas.draw_idle()
        self.kpi.setText('Ошибка при построении.')
        QMessageBox.critical(self, 'Ошибка', message)

    def _set_busy(self, busy: bool) -> None:
        self.btn_build.setEnabled(not busy)
        self.btn_build.setText('Считаю…' if busy else 'Построить')
        if busy:
            self.kpi.setText('Считаю…')

    def shutdown(self) -> None:
        """Дожидается фонового расчёта перед закрытием окна.

        Вызывается из MainWindow.closeEvent. Без этого можно словить
        "QThread: Destroyed while thread is still running", если
        закрыть приложение посреди построения графика.
        """
        self._task_runner.shutdown()

    def _reset_axes(self) -> None:
        """
        Полностью сбрасывает оси графика, чтобы не тащить старое состояние.
        """
        self.figure.clear()
        self.ax = self.figure.add_subplot(111)
        self._apply_theme()

    def _apply_theme(self) -> None:
        """Красит фигуру/оси под текущую системную тему.

        matplotlib понятия не имеет о теме Qt-приложения — рисует
        всегда чёрным по белому, пока ему явно не сказать иначе.
        Вызывается при каждом _reset_axes(), поэтому смена темы ОС
        подхватится на следующем построении графика (не мгновенно —
        живое обновление уже открытого графика без пересчёта данных
        сюда не входило, это отдельная и не факт что нужная фича).
        """
        self._theme = _DARK_COLORS if _is_dark_mode() else _LIGHT_COLORS

        self.figure.patch.set_facecolor(self._theme['figure_bg'])
        self.ax.set_facecolor(self._theme['axes_bg'])

        for spine in self.ax.spines.values():
            spine.set_color(self._theme['grid'])

        self.ax.tick_params(colors=self._theme['text'])
        self.ax.xaxis.label.set_color(self._theme['text'])
        self.ax.yaxis.label.set_color(self._theme['text'])
        self.ax.title.set_color(self._theme['text'])

    def _format_xaxis(self) -> None:
        """Ставит аккуратный автолокатор/форматтер дат для оси X."""
        locator = mdates.AutoDateLocator(minticks=3, maxticks=9)
        formatter = mdates.ConciseDateFormatter(locator)
        self.ax.xaxis.set_major_locator(locator)
        self.ax.xaxis.set_major_formatter(formatter)

    def _annotate_prices(
        self, dfp: pd.DataFrame, mask: pd.Series, x_list: list, y_list: list
    ) -> None:
        """Подписывает фактическую цену за единицу над каждой точкой.

        Есть только у product_index — там один товар, одна цена за
        период, подпись однозначна. У category_index/store_index точка
        графика — это взвешенный индекс Ласпейреса по КОРЗИНЕ разных
        товаров с разными единицами измерения; единой "цены" для такой
        точки просто не существует, поэтому там аннотаций нет — и не
        должно быть, а не "забыли добавить".

        Молчит и при большом числе точек (> _MAX_ANNOTATED_POINTS) —
        иначе подписи налезают друг на друга плотнее, чем сами точки.
        """
        if 'avg_unit_price' not in dfp.columns:
            return
        if len(x_list) > _MAX_ANNOTATED_POINTS:
            return

        prices = pd.to_numeric(dfp['avg_unit_price'], errors='coerce')[
            mask
        ].tolist()

        for xi, yi, price in zip(x_list, y_list, prices):
            if price is None or pd.isna(price):
                continue
            self.ax.annotate(
                f'{price:.2f}',
                xy=(xi, yi),
                xytext=(0, 10),
                textcoords='offset points',
                ha='center',
                fontsize=8,
                color=self._theme['text'],
            )

    def _plot_index(self, res: dict, *, title: str, group_by: str) -> None:
        """Рисует линейный график индекса (база=100).

        Args:
            res: Результат аналитики (points + kpi).
            title: Заголовок графика.
            group_by: Период агрегации для корректного паддинга при 1 точке.
        """
        points = res.get('points') or []
        kpi = res.get('kpi')

        self._reset_axes()

        if not points:
            self.canvas.draw_idle()
            self.kpi.setText('Нет данных под выбранные фильтры.')
            return

        dfp = pd.DataFrame(points)
        if 'period' not in dfp.columns:
            self.canvas.draw_idle()
            self.kpi.setText('Нет данных под выбранные фильтры.')
            return

        x = pd.to_datetime(dfp['period'], errors='coerce')

        y = dfp.get('index_100')
        if y is None:
            y = dfp.get('index')
        if y is None:
            self.canvas.draw_idle()
            self.kpi.setText('Нет данных под выбранные фильтры.')
            return

        y = pd.to_numeric(y, errors='coerce')

        mask = x.notna() & y.notna()
        x = x[mask]
        y = y[mask]
        if len(x) == 0:
            self.canvas.draw_idle()
            self.kpi.setText('Нет данных под выбранные фильтры.')
            return

        self.ax.axhline(
            100, linestyle='--', linewidth=1, color=self._theme['baseline']
        )

        x_list = x.tolist()
        y_list = y.astype(float).tolist()
        gap_threshold = pd.Timedelta(
            days=_GAP_BREAK_DAYS.get(group_by, 30)
        )

        # Рисуем линию отдельными сегментами, разрывая её там, где между
        # соседними покупками прошло больше gap_threshold — иначе
        # matplotlib честно, но обманчиво интерполирует прямой между
        # двумя точками, разнесёнными на месяцы, будто там был плавный
        # тренд. Маркеры рисуем отдельно поверх, на ВСЕХ точках сразу —
        # разрыв линии не должен прятать сами наблюдения.
        seg_x, seg_y = [x_list[0]], [y_list[0]]
        for i in range(1, len(x_list)):
            if x_list[i] - x_list[i - 1] > gap_threshold:
                self.ax.plot(
                    seg_x, seg_y, color=self._theme['line'], linewidth=1.5
                )
                seg_x, seg_y = [], []
            seg_x.append(x_list[i])
            seg_y.append(y_list[i])
        self.ax.plot(seg_x, seg_y, color=self._theme['line'], linewidth=1.5)

        self.ax.plot(
            x_list, y_list,
            linestyle='none', marker='o', color=self._theme['line'],
        )
        self._annotate_prices(dfp, mask, x_list, y_list)
        self.ax.set_title(title, pad=14, fontsize=12, fontweight='bold')
        self.ax.set_ylabel('Индекс')
        self.ax.grid(True, color=self._theme['grid'], alpha=0.5)

        self._format_xaxis()

        if len(x) == 1:
            d0 = x.iloc[0]
            if group_by == 'day':
                pad = pd.Timedelta(days=7)
            elif group_by == 'week':
                pad = pd.Timedelta(days=21)
            elif group_by == 'month':
                pad = pd.Timedelta(days=45)
            else:
                pad = pd.Timedelta(days=400)
            self.ax.set_xlim(d0 - pad, d0 + pad)

        self.figure.tight_layout()
        self.canvas.draw_idle()

        if isinstance(kpi, dict):
            extra: list[str] = []
            if 'coverage_last' in kpi:
                extra.append(
                    'Покрытие (последний период): '
                    f'{float(kpi["coverage_last"]):.2f}'
                )
            if 'inflation_total' in kpi and kpi['inflation_total'] is not None:
                extra.append(
                    'Инфляция от базы: '
                    f'{float(kpi["inflation_total"]):.2f} п.п.')
            if not extra and 'last_n' in kpi:
                extra.append(
                    f'Записей в последнем периоде: {kpi.get("last_n")}'
                )
            self.kpi.setText('\n'.join(extra) if extra else 'Готово.')
        else:
            self.kpi.setText('Готово.')

    def _build_plot_title(
        self,
        *,
        kind: str,
        obj_name: str,
        group_by: str,
        price_mode: str,
        promo_mode: str,
        from_date: Optional[date],
        to_date: Optional[date],
        index_method: Optional[str] = None,
    ) -> str:
        kind_map = {
            'product_index': 'Индекс цен по продукту',
            'category_index': 'Индекс цен по категории',
            'store_index': 'Индекс цен по магазину',
        }
        group_map = {
            'day': 'день',
            'week': 'неделя',
            'month': 'месяц',
            'year': 'год',
        }
        price_map = {
            'paid': 'фактическая цена',
            'regular': 'обычная цена',
        }
        promo_map = {
            'include': 'акции включены',
            'exclude': 'без акций',
            'only': 'только акции',
        }
        method_map = {
            'laspeyres': 'Ласпейрес',
            'paasche': 'Пааше',
            'fisher': 'Фишер',
        }

        line1 = f'{kind_map.get(kind, "Индекс")} — {obj_name}'
        if index_method:
            line1 += f' ({method_map.get(index_method, index_method)})'
        line2 = (
            f'Период: {group_map.get(group_by, group_by)} • '
            f'{price_map.get(price_mode, price_mode)} • '
            f'{promo_map.get(promo_mode, promo_mode)}'
        )

        if from_date and to_date:
            line2 += f' • {from_date:%d.%m.%Y}–{to_date:%d.%m.%Y}'

        return f'{line1}\n{line2}'
