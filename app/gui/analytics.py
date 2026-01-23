from __future__ import annotations

from datetime import date

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
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from app.crud import product_crud
from app.gui.data_manager import DataManagerDialog
from app.service.crud_service import list_items
from app.service.purchases import get_purchase_by_product

_GROUP_FREQ = {
    "День": "D",
    "Неделя": "W-MON",
    "Месяц": "MS",
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
        self.product_combo = QComboBox()

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
        for k in _GROUP_FREQ:
            self.group_combo.addItem(k, _GROUP_FREQ[k])

        self.price_mode = QComboBox()
        self.price_mode.addItem("Как заплатил (paid)", "paid")
        self.price_mode.addItem("Обычная цена (regular)", "regular")

        self.promo_mode = QComboBox()
        self.promo_mode.addItem("Включая акции", "include")
        self.promo_mode.addItem("Без акций", "exclude")
        self.promo_mode.addItem("Только акции", "only")

        left_form = QFormLayout()
        left_form.addRow("Продукт:", self.product_combo)
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

    def _toggle_dates(self) -> None:
        enabled = self.use_dates.isChecked()
        self.date_from.setEnabled(enabled)
        self.date_to.setEnabled(enabled)

    def reload_products(self) -> None:
        self.product_combo.clear()
        self.product_combo.addItem("— выбери продукт —", None)
        products = list_items(product_crud, limit=5000)
        for p in products:
            unit = f"{p.unit.measure_type} {p.unit.unit}" if p.unit else ""
            self.product_combo.addItem(f"{p.name} ({unit}) (id={p.id})", p.id)

    def open_data_manager(self) -> None:
        dlg = DataManagerDialog(self)
        dlg.exec()

        # после закрытия — обновим справочники и, при желании, график
        self.reload_products()

    def build(self) -> None:
        product_id = self.product_combo.currentData()
        if product_id is None:
            QMessageBox.information(self, "Ок", "Сначала выбери продукт.")
            return

        from_date = None
        to_date = None
        if self.use_dates.isChecked():
            from_date = self.date_from.date().toPyDate()
            to_date = self.date_to.date().toPyDate()

        promo_mode = self.promo_mode.currentData()
        is_promo = None
        if promo_mode == "exclude":
            is_promo = False
        elif promo_mode == "only":
            is_promo = True

        price_mode = self.price_mode.currentData()
        freq = self.group_combo.currentData()

        purchases = get_purchase_by_product(
            product_id=product_id,
            from_date=from_date,
            to_date=to_date,
            is_promo=is_promo,
        )

        if not purchases:
            self.ax.clear()
            self.canvas.draw()
            self.kpi.setText("Нет данных под выбранные фильтры.")
            return

        df = pd.DataFrame([p.to_dict() for p in purchases])
        df["purchase_date"] = pd.to_datetime(df["purchase_date"])
        df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
        df["total_price"] = pd.to_numeric(df["total_price"], errors="coerce")
        df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce")
        df["regular_unit_price"] = pd.to_numeric(
            df["regular_unit_price"],
            errors="coerce"
        )

        if price_mode == "paid":
            df["effective_total"] = df["total_price"]
        else:
            eff_unit = df["regular_unit_price"].fillna(df["unit_price"])
            df["effective_total"] = eff_unit * df["quantity"]

        df = df.set_index("purchase_date").sort_index()

        agg = df.resample(freq).agg(
            total=("effective_total", "sum"),
            qty=("quantity", "sum"),
            n=("id", "count"),
        )
        agg["avg_unit_price"] = agg["total"] / agg["qty"]
        agg = agg.dropna(subset=["avg_unit_price"])

        if agg.empty:
            self.ax.clear()
            self.canvas.draw()
            self.kpi.setText(
                "После агрегации данных не осталось (проверь количество/цены)."
            )
            return

        base = float(agg["avg_unit_price"].iloc[0])
        last = float(agg["avg_unit_price"].iloc[-1])
        agg["index_100"] = (agg["avg_unit_price"] / base) * 100.0
        inflation_pct = (last / base - 1.0) * 100.0

        # --- график ---
        self.ax.clear()
        self.ax.axhline(100, linestyle="--", linewidth=1)  # линия базы

        if len(agg) == 1:
            # одна точка — рисуем точкой и ужимаем X
            self.ax.scatter(agg.index, agg["index_100"])
            x = agg.index[0]
            self.ax.set_xlim(
                x - pd.Timedelta(days=20),
                x + pd.Timedelta(days=20)
            )
        else:
            self.ax.plot(agg.index, agg["index_100"], marker="o")

        self.ax.set_title("Индекс инфляции по продукту (база=100)")
        self.ax.set_ylabel("Индекс")
        self.ax.grid(True)
        self.figure.tight_layout()
        self.canvas.draw()

        periods = len(agg)
        if periods < 2:
            inflation_text = "— (нужны минимум 2 периода)"
        else:
            inflation_text = f"{inflation_pct:.2f}%"

        data_start = df.index.min().date().isoformat()
        data_end = df.index.max().date().isoformat()
        self.kpi.setText(
            f"Период: {data_start} — {data_end}\n"
            f"База: {base:.2f}\n"
            f"Текущая: {last:.2f}\n"
            f"Инфляция за период: {inflation_text}%\n"
            f"Записей: {int(agg['n'].sum())}"
        )
