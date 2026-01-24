from __future__ import annotations

from datetime import date
from typing import Optional

import matplotlib.dates as mdates
import numpy as np
import pandas as pd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from app.crud import category_crud, product_crud, store_crud
from app.gui.data_manager import DataManagerDialog
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


class AnalyticsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._data_min: Optional[date] = None
        self._data_max: Optional[date] = None

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
        self.kind_combo.addItem('Моя инфляция: корзина', 'basket_index')
        self.kind_combo.addItem('Вклад в инфляцию (top)', 'contrib')
        self.kind_combo.addItem('Где дешевле продукт', 'cheapest')

        self.product_combo = QComboBox()
        self.category_combo = QComboBox()
        self.store_combo = QComboBox()

        # ids оставляем только для store_index (ограничить корзину в магазине)
        self.product_ids_edit = QLineEdit()
        self.product_ids_edit.setPlaceholderText(
            'id продуктов через запятую, напр. 1,2,3 (необязательно)'
        )

        self.contrib_by = QComboBox()
        self.contrib_by.addItem('По продуктам', 'product')
        self.contrib_by.addItem('По категориям', 'category')

        # Top только 10/20
        self.contrib_top = QComboBox()
        self.contrib_top.addItem('Top 10', 10)
        self.contrib_top.addItem('Top 20', 20)

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

        self.kind_combo.currentIndexChanged.connect(self._on_kind_changed)

        left_form = QFormLayout()
        left_form.addRow('Тип:', self.kind_combo)
        left_form.addRow('Продукт:', self.product_combo)
        left_form.addRow('Категория:', self.category_combo)
        left_form.addRow('Магазин:', self.store_combo)
        left_form.addRow('Корзина (ids):', self.product_ids_edit)
        left_form.addRow('Вклад:', self.contrib_by)
        left_form.addRow('Top:', self.contrib_top)

        left_form.addRow('', self.use_dates)
        left_form.addRow('с:', self.date_from)
        left_form.addRow('по:', self.date_to)
        left_form.addRow('Группировка:', self.group_combo)
        left_form.addRow('Режим цены:', self.price_mode)
        left_form.addRow('Акции:', self.promo_mode)

        left = QWidget()
        left.setLayout(left_form)

        # --- Правая панель (график + метрики) ---
        self.figure = Figure(figsize=(6, 4))
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)

        self.kpi = QLabel('Выбери параметры и нажми «Построить».')
        self.kpi.setWordWrap(True)

        right = QVBoxLayout()
        right.addWidget(self.canvas, stretch=1)
        right.addWidget(self.kpi, stretch=0)

        right_w = QWidget()
        right_w.setLayout(right)

        splitter = QSplitter()
        splitter.addWidget(left)
        splitter.addWidget(right_w)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        root = QVBoxLayout()
        root.addLayout(top)
        root.addWidget(splitter)
        self.setLayout(root)

        self.reload_products()
        self.reload_categories()
        self.reload_stores()
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

    def reload_products(self) -> None:
        """Перезагружает список продуктов и добавляет счётчик покупок."""
        self.product_combo.clear()
        self.product_combo.addItem('— выбери продукт —', None)

        counts = get_purchase_usage_counts()
        prod_cnt = counts.get('products', {})

        products = list_items(product_crud, limit=5000)
        for p in products:
            unit = ''
            if getattr(p, 'unit', None):
                unit = f'{p.unit.measure_type} {p.unit.unit}'
            cnt = int(prod_cnt.get(p.id, 0))
            self.product_combo.addItem(
                f'{p.name} ({unit}) — {cnt} покупок',
                p.id
            )

    def reload_categories(self) -> None:
        """Перезагружает список категорий и добавляет счётчик покупок."""
        self.category_combo.clear()
        self.category_combo.addItem('— выбери категорию —', None)

        counts = get_purchase_usage_counts()
        cat_cnt = counts.get('categories', {})

        cats = list_items(category_crud, limit=5000)
        for c in cats:
            cnt = int(cat_cnt.get(c.id, 0))
            self.category_combo.addItem(f'{c.name} — {cnt} покупок', c.id)

    def reload_stores(self) -> None:
        """Перезагружает список магазинов и добавляет счётчик покупок."""
        self.store_combo.clear()
        self.store_combo.addItem('— выбери магазин —', None)

        counts = get_purchase_usage_counts()
        store_cnt = counts.get('stores', {})

        stores = list_items(store_crud, limit=5000)
        for s in stores:
            cnt = int(store_cnt.get(s.id, 0))
            self.store_combo.addItem(f'{s.name} — {cnt} покупок', s.id)

    def open_data_manager(self) -> None:
        """Открывает диалог управления данными и обновляет списки."""
        dlg = DataManagerDialog(self)
        dlg.exec()
        self.reload_products()
        self.reload_categories()
        self.reload_stores()
        self._init_date_bounds()

    # ------------------- kind switching -------------------

    def _on_kind_changed(self) -> None:
        """Реакция на смену типа аналитики.

        Делает три вещи:
        1) включает/выключает нужные поля
        2) сбрасывает неиспользуемые поля на дефолтные значения
        3) накладывает ограничения (например, корзина только по месяцам)
        """
        kind = self.kind_combo.currentData()

        need_product = kind in {'product_index', 'cheapest'}
        need_category = kind == 'category_index'
        need_store = kind == 'store_index'
        need_ids = kind == 'store_index'
        need_contrib = kind == 'contrib'

        self.product_combo.setEnabled(need_product)
        self.category_combo.setEnabled(need_category)
        self.store_combo.setEnabled(need_store)
        self.product_ids_edit.setEnabled(need_ids)
        self.contrib_by.setEnabled(need_contrib)
        self.contrib_top.setEnabled(need_contrib)

        # reset disabled inputs
        if not need_product:
            self.product_combo.setCurrentIndex(0)
        if not need_category:
            self.category_combo.setCurrentIndex(0)
        if not need_store:
            self.store_combo.setCurrentIndex(0)
        if not need_ids:
            self.product_ids_edit.setText('')
        if not need_contrib:
            self.contrib_by.setCurrentIndex(0)
            self.contrib_top.setCurrentIndex(0)

        # сбрасываем фильтр дат при смене аналитики
        self.use_dates.setChecked(False)
        self._toggle_dates()

        # корзина: принудительно месяцы
        if kind == 'basket_index':
            self._set_group_by('month')
            self.group_combo.setEnabled(False)
        else:
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

    # ------------------- build + plots -------------------

    def build(self) -> None:
        """Собирает параметры, вызывает аналитику и отрисовывает график."""
        kind = self.kind_combo.currentData()
        if not kind:
            QMessageBox.information(self, 'Ок', 'Выбери тип аналитики.')
            return

        from_date = None
        to_date = None
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

        if kind == 'basket_index':
            group_by = 'month'

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

                res = svc.product_inflation_index(
                    product_id=int(product_id),
                    from_date=from_date,
                    to_date=to_date,
                    group_by=group_by,
                    price_mode=price_mode,
                    promo_mode=promo_mode,
                )
                self._plot_index(
                    res,
                    title='Индекс по продукту (база=100)',
                    group_by=group_by
                )

            elif kind == 'category_index':
                category_id = self.category_combo.currentData()
                if category_id is None:
                    QMessageBox.information(
                        self,
                        'Ок',
                        'Сначала выбери категорию.'
                    )
                    return

                res = svc.category_inflation_index(
                    category_id=int(category_id),
                    from_date=from_date,
                    to_date=to_date,
                    group_by=group_by,
                    price_mode=price_mode,
                    promo_mode=promo_mode,
                )
                self._plot_index(
                    res,
                    title='Индекс по категории (база=100)',
                    group_by=group_by
                )

            elif kind == 'store_index':
                store_id = self.store_combo.currentData()
                if store_id is None:
                    QMessageBox.information(
                        self,
                        'Ок',
                        'Сначала выбери магазин.'
                    )
                    return

                res = svc.store_inflation_index(
                    store_id=int(store_id),
                    from_date=from_date,
                    to_date=to_date,
                    product_ids=product_ids,
                    group_by=group_by,
                    price_mode=price_mode,
                    promo_mode=promo_mode,
                )
                self._plot_index(
                    res,
                    title='Индекс по магазину (база=100)',
                    group_by=group_by
                )

            elif kind == 'basket_index':
                res = svc.basket_inflation_index(
                    from_date=from_date,
                    to_date=to_date,
                    product_ids=None,
                    group_by=group_by,
                    price_mode=price_mode,
                    promo_mode=promo_mode,
                )
                self._plot_index(
                    res,
                    title='Моя инфляция (корзина, база=100)',
                    group_by=group_by
                )

            elif kind == 'contrib':
                top_n = int(self.contrib_top.currentData() or 10)
                by = self.contrib_by.currentData() or 'product'

                res, used_group_by = self._contrib_with_fallback(
                    by=by,
                    from_date=from_date,
                    to_date=to_date,
                    group_by=str(group_by),
                    price_mode=str(price_mode),
                    promo_mode=str(promo_mode),
                    top=top_n,
                )
                title = f'Вклад в инфляцию (Top {top_n}, {used_group_by})'
                self._plot_contrib(res, title=title)

            elif kind == 'cheapest':
                product_id = self.product_combo.currentData()
                if product_id is None:
                    QMessageBox.information(
                        self,
                        'Ок',
                        'Сначала выбери продукт.'
                    )
                    return

                res = svc.product_store_price_stats(
                    product_id=int(product_id),
                    from_date=from_date,
                    to_date=to_date,
                    price_mode=price_mode,
                    promo_mode=promo_mode,
                )
                self._plot_cheapest(res, title='Средняя цена по магазинам')

            else:
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

    def _contrib_with_fallback(
        self,
        *,
        by: str,
        from_date: Optional[date],
        to_date: Optional[date],
        group_by: str,
        price_mode: str,
        promo_mode: str,
        top: int,
    ) -> tuple[dict, str]:
        """Строит вклад в инфляцию с автоматическим уменьшением периода.

        Частая причина 'пустого' вклада:
        month + даты внутри одного месяца =>
        base_period == target_period => вклад ~0.
        Поэтому пробуем уменьшить период: year -> month -> week -> day.

        Args:
            by: Группировка вклада: 'product' или 'category'.
            from_date: Дата начала фильтра (опционально).
            to_date: Дата конца фильтра (опционально).
            group_by: Исходная группировка периодов.
            price_mode: 'paid' или 'regular'.
            promo_mode: 'include'/'exclude'/'only'.
            top: Сколько элементов вернуть.

        Returns:
            Кортеж:
            - результат аналитики
            - фактически использованный group_by
        """
        def _is_degenerate(res: dict) -> bool:
            k = res.get('kpi') or {}
            base = k.get('base_period')
            target = k.get('target_period')
            if base and target and base == target:
                return True

            pts = res.get('points') or []
            if not pts:
                return True

            vals = [
                float(p.get('contribution', 0.0))
                for p in pts
                if p.get('contribution') is not None
            ]
            return (len(vals) == 0) or (max(abs(v) for v in vals) < 1e-9)

        order = ['year', 'month', 'week', 'day']
        if group_by not in order:
            group_by = 'month'

        start_idx = order.index(group_by)
        last_res: dict = {'points': [], 'kpi': {}}

        for gb in order[start_idx:]:
            res = svc.inflation_contributions(
                by=by,
                from_date=from_date,
                to_date=to_date,
                product_ids=None,
                store_id=None,
                category_id=None,
                group_by=gb,
                price_mode=price_mode,
                promo_mode=promo_mode,
                top=int(top),
            )
            last_res = res
            if not _is_degenerate(res):
                return res, gb

        return last_res, 'day'

    def _reset_axes(self) -> None:
        """
        Полностью сбрасывает оси графика, чтобы не тащить старое состояние.
        """
        self.figure.clear()
        self.ax = self.figure.add_subplot(111)

    def _format_xaxis(self) -> None:
        """Ставит аккуратный автолокатор/форматтер дат для оси X."""
        locator = mdates.AutoDateLocator(minticks=3, maxticks=9)
        formatter = mdates.ConciseDateFormatter(locator)
        self.ax.xaxis.set_major_locator(locator)
        self.ax.xaxis.set_major_formatter(formatter)

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

        self.ax.axhline(100, linestyle='--', linewidth=1)
        self.ax.plot(x.tolist(), y.astype(float).tolist(), marker='o')
        self.ax.set_title(title)
        self.ax.set_ylabel('Индекс')
        self.ax.grid(True)

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

    def _plot_contrib(self, res: dict, *, title: str) -> None:
        """Рисует вклад в инфляцию (горизонтальные бары).

        Args:
            res: Результат аналитики (points + kpi).
            title: Заголовок графика.
        """
        points = res.get('points') or []
        kpi = res.get('kpi') or {}

        self._reset_axes()

        if not points:
            self.canvas.draw_idle()
            self.kpi.setText(
                'Нет данных для вклада (нужны база и последний период).'
            )
            return

        labels: list[str] = []
        vals: list[float] = []
        for p in points:
            label = (
                p.get('product')
                or p.get('category')
                or str(p.get('product_id') or p.get('category_id'))
            )
            label = str(label)
            if len(label) > 40:
                label = label[:37] + '…'
            labels.append(label)
            vals.append(float(p.get('contribution', 0.0)))

        if max(abs(v) for v in vals) < 1e-9:
            base = kpi.get('base_period')
            target = kpi.get('target_period')
            self.canvas.draw_idle()
            self.kpi.setText(
                'Вклад получился нулевой.\n'
                f'База: {base} → {target}\n'
                'Скорее всего, диапазон дат попал в один период группировки.\n'
                'Расширь диапазон дат или выбери более мелкую группировку.'
            )
            return

        order = np.argsort(vals)[::-1]
        labels = [labels[i] for i in order]
        vals = [vals[i] for i in order]

        self.ax.axvline(0, linestyle='--', linewidth=1)
        self.ax.barh(labels, vals)
        self.ax.invert_yaxis()
        self.ax.set_title(title)
        self.ax.set_xlabel('Пункты индекса')
        self.ax.grid(True, axis='x')

        self.figure.tight_layout()
        self.canvas.draw_idle()

        self.kpi.setText(
            f'База: {kpi.get("base_period")} → {kpi.get("target_period")}\n'
            f'Покрытый вес: {kpi.get("covered_weight")}'
        )

    def _plot_cheapest(self, res: dict, *, title: str) -> None:
        """Рисует 'где дешевле продукт'

        (горизонтальные бары, сортировка по цене).

        Args:
            res: Результат аналитики (points + kpi).
            title: Заголовок графика.
        """
        points = res.get('points') or []
        kpi = res.get('kpi') or {}

        self._reset_axes()

        if not points:
            self.canvas.draw_idle()
            self.kpi.setText('Нет данных под выбранные фильтры.')
            return

        labels = [str(p.get('store')) for p in points]
        vals = [float(p.get('avg_unit_price', 0.0)) for p in points]

        order = np.argsort(vals)
        labels = [labels[i] for i in order]
        vals = [vals[i] for i in order]

        self.ax.barh(labels, vals)
        self.ax.invert_yaxis()
        self.ax.set_title(title)
        self.ax.set_xlabel('Цена за единицу')
        self.ax.grid(True, axis='x')

        self.figure.tight_layout()
        self.canvas.draw_idle()

        best_avg = kpi.get('best_avg_unit_price')
        best_avg_s = (
            f'{best_avg:.2f}' if isinstance(
                best_avg, (int, float)
            ) else str(best_avg)
        )
        self.kpi.setText(
            f'Магазинов: {kpi.get("stores")}\n'
            f'Лучший: id={kpi.get("best_store_id")} (avg={best_avg_s})'
        )
