from __future__ import annotations

from datetime import date
from typing import Optional

import pandas as pd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.dates as mdates
from matplotlib.ticker import Formatter, Locator
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

_GROUP_FREQ = {
    "День": "day",
    "Неделя": "week",
    "Месяц": "month",
    "Год": "year",
}


class AnalyticsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # --- Верхняя панель (кнопки) ---
        self.btn_data = QPushButton("Данные…")
        self.btn_build = QPushButton("Построить")

        self.btn_data.clicked.connect(self.open_data_manager)
        self.btn_build.clicked.connect(self.build)

        top = QHBoxLayout()
        top.addWidget(self.btn_data)
        top.addStretch(1)
        top.addWidget(self.btn_build)

        # --- Левая панель параметров ---
        self.kind_combo = QComboBox()
        self.kind_combo.addItem("Продукт: индекс", "product_index")
        self.kind_combo.addItem("Категория: индекс", "category_index")
        self.kind_combo.addItem("Магазин: индекс", "store_index")
        self.kind_combo.addItem("Моя инфляция: корзина", "basket_index")
        self.kind_combo.addItem("Вклад в инфляцию (top)", "contrib")
        self.kind_combo.addItem("Где дешевле продукт", "cheapest")

        self.product_combo = QComboBox()
        self.category_combo = QComboBox()
        self.store_combo = QComboBox()

        # ids — только для store_index (ограничить корзину магазина)
        self.product_ids_edit = QLineEdit()
        self.product_ids_edit.setPlaceholderText(
            "id продуктов через запятую, напр. 1,2,3"
            "(только для 'Магазин: индекс')"
        )

        self.contrib_by = QComboBox()
        self.contrib_by.addItem("По продуктам", "product")
        self.contrib_by.addItem("По категориям", "category")

        # Top 10/20 (не SpinBox)
        self.contrib_top = QComboBox()
        self.contrib_top.addItem("Top 10", 10)
        self.contrib_top.addItem("Top 20", 20)

        self.kind_combo.currentIndexChanged.connect(self._toggle_kind_fields)

        self.use_dates = QCheckBox("Фильтр по датам")
        self.date_from = QDateEdit()
        self.date_to = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_to.setCalendarPopup(True)

        today = date.today()
        self.date_from.setDate(QDate(today.year, today.month, 1))
        self.date_to.setDate(QDate(today.year, today.month, today.day))
        self.date_from.setEnabled(False)
        self.date_to.setEnabled(False)
        self.use_dates.stateChanged.connect(self._toggle_dates)

        self.group_combo = QComboBox()
        for k, v in _GROUP_FREQ.items():
            self.group_combo.addItem(k, v)

        self.price_mode = QComboBox()
        self.price_mode.addItem("Как заплатил (paid)", "paid")
        self.price_mode.addItem("Обычная цена (regular)", "regular")

        self.promo_mode = QComboBox()
        self.promo_mode.addItem("Включая акции", "include")
        self.promo_mode.addItem("Без акций", "exclude")
        self.promo_mode.addItem("Только акции", "only")

        left_form = QFormLayout()

        # Сначала "что строим"
        left_form.addRow("Тип:", self.kind_combo)
        left_form.addRow("Продукт:", self.product_combo)
        left_form.addRow("Категория:", self.category_combo)
        left_form.addRow("Магазин:", self.store_combo)
        left_form.addRow("Корзина (ids):", self.product_ids_edit)
        left_form.addRow("Вклад:", self.contrib_by)
        left_form.addRow("Top:", self.contrib_top)

        # Потом общие фильтры
        left_form.addRow("", self.use_dates)
        left_form.addRow("с:", self.date_from)
        left_form.addRow("по:", self.date_to)
        left_form.addRow("Группировка:", self.group_combo)
        left_form.addRow("Режим цены:", self.price_mode)
        left_form.addRow("Акции:", self.promo_mode)

        left = QWidget()
        left.setLayout(left_form)

        # --- Правая панель (график + метрики) ---
        self.figure = Figure(figsize=(6, 4))
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)

        self.kpi = QLabel("Выбери параметры и нажми «Построить».")
        self.kpi.setWordWrap(True)

        right = QVBoxLayout()
        right.addWidget(self.canvas, stretch=1)
        right.addWidget(self.kpi, stretch=0)

        right_w = QWidget()
        right_w.setLayout(right)

        # --- Splitter (лево/право) ---
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
        self._toggle_kind_fields()

    # -------------------------
    # UI helpers
    # -------------------------
    def _toggle_dates(self) -> None:
        enabled = self.use_dates.isChecked()
        self.date_from.setEnabled(enabled)
        self.date_to.setEnabled(enabled)

    def _set_combo_data(self, combo: QComboBox, value: str) -> None:
        idx = combo.findData(value)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    def _reset_axes(self) -> None:
        # Полный reset состояния графика (локаторы/форматтеры/scale и т.п.)
        self.figure.clear()
        self.ax = self.figure.add_subplot(111)

    def _reset_unused_fields(
        self,
        *,
        need_product: bool,
        need_category: bool,
        need_store: bool,
        need_ids: bool,
        need_contrib: bool,
    ) -> None:
        if not need_product:
            self.product_combo.setCurrentIndex(0)
        if not need_category:
            self.category_combo.setCurrentIndex(0)
        if not need_store:
            self.store_combo.setCurrentIndex(0)
        if not need_ids:
            self.product_ids_edit.clear()
        if not need_contrib:
            self.contrib_by.setCurrentIndex(0)
            self.contrib_top.setCurrentIndex(0)

    def _toggle_kind_fields(self) -> None:
        kind = self.kind_combo.currentData()

        need_product = kind in {"product_index", "cheapest"}
        need_category = kind == "category_index"
        need_store = kind == "store_index"
        need_ids = kind == "store_index"
        need_contrib = kind == "contrib"

        # Сброс неиспользуемых полей на дефолт
        self._reset_unused_fields(
            need_product=need_product,
            need_category=need_category,
            need_store=need_store,
            need_ids=need_ids,
            need_contrib=need_contrib,
        )

        # Enable/Disable
        self.product_combo.setEnabled(need_product)
        self.category_combo.setEnabled(need_category)
        self.store_combo.setEnabled(need_store)
        self.product_ids_edit.setEnabled(need_ids)

        self.contrib_by.setEnabled(need_contrib)
        self.contrib_top.setEnabled(need_contrib)

        if kind == "cheapest" or kind == "basket_index":
            self.group_combo.setEnabled(False)
            self._set_combo_data(self.group_combo, "month")
        else:
            self.group_combo.setEnabled(True)

    # -------------------------
    # Reload data (with counts)
    # -------------------------
    def reload_products(self) -> None:
        self.product_combo.clear()
        self.product_combo.addItem("— выбери продукт —", None)

        counts = svc.purchase_counts(by="product")
        products = list_items(product_crud, limit=5000)
        for p in products:
            unit = f"{p.unit.measure_type} {p.unit.unit}" if getattr(
                p, "unit", None
            ) else ""
            n = counts.get(int(p.id), 0)
            self.product_combo.addItem(
                f"{p.name} ({unit}) (покупок: {n})", p.id
            )

    def reload_categories(self) -> None:
        self.category_combo.clear()
        self.category_combo.addItem("— выбери категорию —", None)

        counts = svc.purchase_counts(by="category")
        cats = list_items(category_crud, limit=5000)
        for c in cats:
            n = counts.get(int(c.id), 0)
            self.category_combo.addItem(f"{c.name} (покупок: {n})", c.id)

    def reload_stores(self) -> None:
        self.store_combo.clear()
        self.store_combo.addItem("— выбери магазин —", None)

        counts = svc.purchase_counts(by="store")
        stores = list_items(store_crud, limit=5000)
        for s in stores:
            n = counts.get(int(s.id), 0)
            self.store_combo.addItem(f"{s.name} (покупок: {n})", s.id)

    def open_data_manager(self) -> None:
        dlg = DataManagerDialog(self)
        dlg.exec()
        self.reload_products()
        self.reload_categories()
        self.reload_stores()
        self._toggle_kind_fields()

    # -------------------------
    # Build
    # -------------------------
    def build(self) -> None:
        kind = self.kind_combo.currentData()
        if not kind:
            QMessageBox.information(self, "Ок", "Выбери тип аналитики.")
            return

        from_date = None
        to_date = None
        if self.use_dates.isChecked():
            from_date = self.date_from.date().toPyDate()
            to_date = self.date_to.date().toPyDate()
            if from_date and to_date and from_date > to_date:
                QMessageBox.information(
                    self,
                    "Ок",
                    "Дата 'с' не может быть позже даты 'по'."
                )
                return

        group_by = self.group_combo.currentData() or "month"
        price_mode = self.price_mode.currentData() or "paid"
        promo_mode = self.promo_mode.currentData() or "include"

        # Корзина — всегда месяц
        if kind == "basket_index":
            group_by = "month"

        # ids нужны только для store_index
        product_ids = None
        if kind == "store_index":
            try:
                product_ids = self._parse_ids()
            except ValueError as e:
                QMessageBox.information(self, "Ошибка", str(e))
                return

        try:
            if kind == "product_index":
                product_id = self.product_combo.currentData()
                if product_id is None:
                    QMessageBox.information(
                        self,
                        "Ок",
                        "Сначала выбери продукт."
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
                    title="Индекс по продукту (база=100)",
                    group_by=group_by
                )

            elif kind == "category_index":
                category_id = self.category_combo.currentData()
                if category_id is None:
                    QMessageBox.information(
                        self,
                        "Ок",
                        "Сначала выбери категорию."
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
                    title="Индекс по категории (база=100)",
                    group_by=group_by
                )

            elif kind == "store_index":
                store_id = self.store_combo.currentData()
                if store_id is None:
                    QMessageBox.information(
                        self,
                        "Ок",
                        "Сначала выбери магазин."
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
                    title="Индекс по магазину (база=100)",
                    group_by=group_by
                )

            elif kind == "basket_index":
                res = svc.basket_inflation_index(
                    from_date=from_date,
                    to_date=to_date,
                    product_ids=None,
                    group_by="month",
                    price_mode=price_mode,
                    promo_mode=promo_mode,
                )
                self._plot_index(
                    res,
                    title="Моя инфляция (корзина, месяц, база=100)",
                    group_by="month"
                )

            elif kind == "contrib":
                top_n = int(self.contrib_top.currentData() or 10)
                res = svc.inflation_contributions(
                    by=self.contrib_by.currentData() or "product",
                    from_date=from_date,
                    to_date=to_date,
                    product_ids=None,
                    group_by=group_by,
                    price_mode=price_mode,
                    promo_mode=promo_mode,
                    top=top_n,
                )
                self._plot_contrib(
                    res,
                    title=f"Вклад в инфляцию (Top {top_n})"
                )

            elif kind == "cheapest":
                product_id = self.product_combo.currentData()
                if product_id is None:
                    QMessageBox.information(
                        self, "Ок", "Сначала выбери продукт."
                    )
                    return

                res = svc.product_store_price_stats(
                    product_id=int(product_id),
                    from_date=from_date,
                    to_date=to_date,
                    price_mode=price_mode,
                    promo_mode=promo_mode,
                )
                self._plot_cheapest(res, title="Средняя цена по магазинам")

            else:
                QMessageBox.information(
                    self, "Ок", f"Неизвестный тип аналитики: {kind}"
                )
                return

        except Exception as e:
            self._reset_axes()
            self.canvas.draw()
            self.kpi.setText("Ошибка при построении.")
            QMessageBox.critical(self, "Ошибка", str(e))
            return

    # -------------------------
    # Parsers
    # -------------------------
    def _parse_ids(self) -> Optional[list[int]]:
        raw = (self.product_ids_edit.text() or "").strip()
        if not raw:
            return None
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        ids: list[int] = []
        for p in parts:
            if not p.isdigit():
                raise ValueError(f"Некорректный id: {p}")
            ids.append(int(p))
        return ids or None

    # -------------------------
    # Plotters
    # -------------------------
    def _plot_index(self, res: dict, *, title: str, group_by: str) -> None:
        points = res.get("points") or []
        kpi = res.get("kpi")

        self._reset_axes()

        if not points:
            self.canvas.draw()
            self.kpi.setText("Нет данных под выбранные фильтры.")
            return

        # Нормализуем group_by на случай если прилетит pandas-freq
        gb = (group_by or "month").lower()
        gb = {
            "d": "day",
            "w-mon": "week",
            "w": "week",
            "m": "month",
            "ms": "month",
            "y": "year",
            "a": "year",
        }.get(gb, gb)

        # Собираем точки
        rows: list[dict] = []
        for p in points:
            val = p.get("index_100")
            if val is None:
                val = p.get("index")
            if val is None:
                continue
            rows.append({"period": p.get("period"), "y": float(val)})

        if not rows:
            self.canvas.draw()
            self.kpi.setText("Нет данных под выбранные фильтры.")
            return

        dfp = pd.DataFrame(rows)
        dfp["x"] = pd.to_datetime(dfp["period"], errors="coerce")
        dfp = dfp.dropna(subset=["x"]).sort_values("x")

        if dfp.empty:
            self.canvas.draw()
            self.kpi.setText("Нет данных под выбранные фильтры.")
            return

        x_dt = dfp["x"].dt.to_pydatetime().tolist()
        y = dfp["y"].astype(float).tolist()

        self.ax.axhline(100, linestyle="--", linewidth=1)
        self.ax.plot(x_dt, y, marker="o")
        self.ax.set_title(title)
        self.ax.set_ylabel("Индекс")
        self.ax.grid(True)

        # ---- Локатор/форматтер под период ----
        locator: Locator
        formatter: Formatter
        pad: pd.Timedelta

        n = len(dfp)
        tick_interval = max(1, n // 12)

        if gb == "day":
            locator = mdates.DayLocator(interval=tick_interval)
            formatter = mdates.DateFormatter("%d.%m")
            pad = pd.Timedelta(days=1)

        elif gb == "week":
            locator = mdates.WeekdayLocator(byweekday=mdates.MO, interval=tick_interval)
            formatter = mdates.DateFormatter("%d.%m")
            pad = pd.Timedelta(days=7)

        elif gb == "month":
            locator = mdates.MonthLocator(interval=tick_interval)
            formatter = mdates.DateFormatter("%m.%Y")
            pad = pd.Timedelta(days=31)

        else:  # year
            locator = mdates.YearLocator(base=tick_interval)
            formatter = mdates.DateFormatter("%Y")
            pad = pd.Timedelta(days=366)

        self.ax.xaxis.set_major_locator(locator)
        self.ax.xaxis.set_major_formatter(formatter)

        # ---- Если точка одна — фикс лимитов, чтобы не улетало в эпохи ----
        xmin = dfp["x"].min()
        xmax = dfp["x"].max()
        if xmin == xmax:
            self.ax.set_xlim((xmin - pad).to_pydatetime(), (xmax + pad).to_pydatetime())
        else:
            self.ax.set_xlim(
                (xmin - pad * 0.2).to_pydatetime(),
                (xmax + pad * 0.2).to_pydatetime(),
            )

        self.figure.autofmt_xdate()
        self.canvas.draw()

        # KPI
        if isinstance(kpi, dict):
            extra = [f"Точек: {len(dfp)}", f"Период: {gb}"]
            if "coverage_last" in kpi:
                extra.append(f'Покрытие (последний период): {kpi["coverage_last"]:.2f}')
            if "inflation_total" in kpi and kpi["inflation_total"] is not None:
                extra.append(f'Инфляция от базы: {kpi["inflation_total"]:.2f} п.п.')
            self.kpi.setText("\n".join(extra))
        else:
            self.kpi.setText(f"Готово. Точек: {len(dfp)}")

    def _plot_cheapest(self, res: dict, *, title: str) -> None:
        points = res.get("points") or []
        kpi = res.get("kpi")

        self._reset_axes()

        if not points:
            self.canvas.draw()
            self.kpi.setText("Нет данных под выбранные фильтры.")
            return

        labels = [p["store"] for p in points]
        vals = [float(p["avg_unit_price"]) for p in points]

        self.ax.bar(labels, vals)
        self.ax.set_title(title)
        self.ax.set_ylabel("Цена за единицу")
        self.ax.grid(True, axis="y")
        self.ax.tick_params(axis="x", labelrotation=45)
        self.canvas.draw()

        if isinstance(kpi, dict):
            best_avg = kpi.get("best_avg_unit_price")
            best_avg_s = f"{best_avg:.2f}" if isinstance(
                best_avg, (int, float)
            ) else str(best_avg)
            self.kpi.setText(
                f'Магазинов: {kpi.get("stores")}\n'
                f'Лучший: id={kpi.get("best_store_id")} (avg={best_avg_s})'
            )
        else:
            self.kpi.setText("Готово.")

    def _plot_contrib(self, res: dict, *, title: str) -> None:
        points = res.get("points") or []
        kpi = res.get("kpi")

        self._reset_axes()

        if not points:
            self.canvas.draw()
            self.kpi.setText(
                "Нет данных для вклада (нужны база и последний период)."
            )
            return

        labels: list[str] = []
        vals: list[float] = []
        for p in points:
            labels.append(
                p.get("product")
                or p.get("category")
                or str(p.get("product_id") or p.get("category_id"))
            )
            vals.append(float(p["contribution"]))

        self.ax.bar(labels, vals)
        self.ax.set_title(title)
        self.ax.set_ylabel("Пункты индекса")
        self.ax.grid(True, axis="y")
        self.ax.tick_params(axis="x", labelrotation=45)
        self.canvas.draw()

        if isinstance(kpi, dict):
            self.kpi.setText(
                f'База: {kpi.get("base_period")} →'
                f'{kpi.get("target_period")}\n'
                f'Покрытый вес: {kpi.get("covered_weight")}'
            )
        else:
            self.kpi.setText("Готово.")
