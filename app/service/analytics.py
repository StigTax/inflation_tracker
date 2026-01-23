from __future__ import annotations

from datetime import date
from typing import Any, Literal, Optional

import pandas as pd

from app.service.purchases import get_purchase_by_product

GroupBy = Literal['day', 'week', 'month']
PriceMode = Literal['paid', 'regular']
PromoMode = Literal['include', 'exclude', 'only']

_GROUP_TO_PERIOD = {
    'day': 'D',
    'week': 'W-MON',
    'month': 'M',
}


def product_inflation_index(
    *,
    product_id: int,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    group_by: GroupBy = 'month',
    price_mode: PriceMode = 'paid',
    promo_mode: PromoMode = 'include',
) -> dict[str, Any]:
    purchases = get_purchase_by_product(
        product_id=product_id,
        from_date=from_date,
        to_date=to_date,
        is_promo=None,
    )
    df = pd.DataFrame([p.to_dict() for p in purchases])
    if df.empty:
        return {'points': [], 'kpi': None}

    df["purchase_date"] = pd.to_datetime(df["purchase_date"])
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
    df["total_price"] = pd.to_numeric(df["total_price"], errors="coerce")
    df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce")
    df["regular_unit_price"] = pd.to_numeric(
        df["regular_unit_price"], errors="coerce"
    )

    promo_mask = df["is_promo"].fillna(False).astype(bool)

    if promo_mode == "exclude":
        df = df[~promo_mask]
    elif promo_mode == "only":
        df = df[promo_mask]

    if df.empty:
        return {"points": [], "kpi": None}

    period = _GROUP_TO_PERIOD[group_by]
    df["period"] = df["purchase_date"].dt.to_period(period).dt.start_time

    if price_mode == "paid":
        df["effective_total"] = df["total_price"]
    else:
        eff_unit = df["regular_unit_price"].fillna(df["unit_price"])
        df["effective_total"] = eff_unit * df["quantity"]

    agg = (
        df.groupby("period", as_index=False)
        .agg(
            total=("effective_total", "sum"),
            qty=("quantity", "sum"),
            n=("id", "count"),
        )
    )

    agg["avg_unit_price"] = agg["total"] / agg["qty"]
    agg = agg.sort_values("period")

    base_price = float(agg["avg_unit_price"].iloc[0])
    agg["index"] = agg["avg_unit_price"] / base_price
    agg["index_100"] = agg["index"] * 100.0
    agg["inflation_pct_from_base"] = (agg["index"] - 1.0) * 100.0

    last = agg.iloc[-1]
    prev = agg.iloc[-2] if len(agg) >= 2 else None
    mom_pct = None
    if prev is not None and float(prev["avg_unit_price"]) != 0:
        mom_pct = (float(
            last["avg_unit_price"]
        ) / float(
            prev["avg_unit_price"]
        ) - 1.0) * 100.0

    kpi = {
        "base_period": agg["period"].iloc[0].date().isoformat(),
        "base_price": base_price,
        "last_period": last["period"].date().isoformat(),
        "last_avg_unit_price": float(last["avg_unit_price"]),
        "last_index_100": float(last["index_100"]),
        "change_vs_prev_period_pct": mom_pct,
        "last_n": int(last["n"]),
    }

    points = agg[
        [
            "period",
            "avg_unit_price",
            "index_100",
            "inflation_pct_from_base",
            "n"
        ]
    ].to_dict("records")
    for p in points:
        p["period"] = p["period"].date().isoformat()

    return {'points': points, 'kpi': kpi}
