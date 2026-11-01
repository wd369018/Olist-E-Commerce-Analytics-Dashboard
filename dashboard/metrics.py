"""Business metric calculations.

All functions are pure and receive an :class:`AnalysisContext`. They are written
to tolerate empty frames and zero denominators, which keeps every page safe when
filters return no matching orders.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import STATE_NAMES
from .filters import AnalysisContext
from .formatting import pct, safe_div

NON_DELIVERED = "No delivery data"


def _empty(columns: list[str]) -> pd.DataFrame:
    return pd.DataFrame(columns=columns)


def _month_range(series: pd.Series) -> pd.DatetimeIndex:
    valid = pd.to_datetime(series, errors="coerce").dropna()
    if valid.empty:
        return pd.DatetimeIndex([], name="purchase_month")
    return pd.date_range(valid.min(), valid.max(), freq="MS", name="purchase_month")


def _fill_months(frame: pd.DataFrame, months: pd.DatetimeIndex, columns: list[str]) -> pd.DataFrame:
    if frame.empty and months.empty:
        return _empty(["purchase_month", *columns])
    if months.empty:
        return frame
    result = frame.set_index("purchase_month").reindex(months)
    for column in columns:
        if column not in result.columns:
            result[column] = 0.0
        result[column] = result[column].fillna(0)
    result.index.name = "purchase_month"
    return result.reset_index()


# ---------------------------------------------------------------------------
# Executive / core revenue
# ---------------------------------------------------------------------------
def overview_metrics(ctx: AnalysisContext) -> dict[str, float | int]:
    orders = ctx.orders
    valid_orders = ctx.valid_orders
    items = ctx.valid_items
    total_orders = int(orders["order_id"].nunique()) if not orders.empty else 0
    delivered_orders = int(orders["is_delivered"].sum()) if not orders.empty else 0
    canceled_orders = int(orders["is_canceled"].sum()) if not orders.empty else 0
    product_revenue = float(items["price"].sum()) if not items.empty else 0.0
    gross_revenue = float(items["gross_value"].sum()) if not items.empty else 0.0
    orders_with_items = (
        int(valid_orders.loc[valid_orders["item_count"].gt(0), "order_id"].nunique())
        if not valid_orders.empty
        else 0
    )
    unique_customers = (
        int(valid_orders["customer_unique_id"].nunique()) if not valid_orders.empty else 0
    )
    if unique_customers and not valid_orders.empty:
        frequency = valid_orders.groupby("customer_unique_id")["order_id"].nunique()
        repeat_customers = int(frequency.gt(1).sum())
    else:
        repeat_customers = 0

    reviews = ctx.reviews
    valid_reviews = reviews[reviews["review_score"].between(1, 5)] if not reviews.empty else reviews
    avg_review = float(valid_reviews["review_score"].mean()) if not valid_reviews.empty else float("nan")

    delivered_with_dates = (
        orders[orders["is_delivered"] & orders["has_delivery_dates"]]
        if not orders.empty
        else orders
    )
    avg_delivery_days = (
        float(delivered_with_dates["delivery_days"].mean()) if not delivered_with_dates.empty else float("nan")
    )
    late_rate = (
        pct(delivered_with_dates["is_late"].sum(), len(delivered_with_dates))
        if not delivered_with_dates.empty
        else 0.0
    )

    metrics = {
        "total_orders": total_orders,
        "delivered_orders": delivered_orders,
        "canceled_orders": canceled_orders,
        "delivery_rate": pct(delivered_orders, total_orders),
        "product_revenue": product_revenue,
        "gross_revenue": gross_revenue,
        "freight_revenue": gross_revenue - product_revenue,
        "orders_with_items": orders_with_items,
        "aov": safe_div(product_revenue, orders_with_items),
        "cancellation_rate": pct(canceled_orders, total_orders),
        "unique_customers": unique_customers,
        "repeat_customers": repeat_customers,
        "repeat_rate": pct(repeat_customers, unique_customers),
        "avg_orders_per_customer": safe_div(len(valid_orders), unique_customers),
        "avg_customer_value": safe_div(product_revenue, unique_customers),
        "avg_review_score": avg_review,
        "review_count": int(len(valid_reviews)),
        "review_coverage": pct(len(valid_reviews), total_orders),
        "avg_delivery_days": avg_delivery_days,
        "late_rate": late_rate,
        "payment_total": float(ctx.payments["payment_value"].sum()) if not ctx.payments.empty else 0.0,
        "active_categories": int(items["category"].nunique()) if not items.empty else 0,
        "active_products": int(items["product_id"].nunique()) if not items.empty else 0,
        "active_sellers": int(items["seller_id"].nunique()) if not items.empty else 0,
    }
    return metrics


def monthly_sales(ctx: AnalysisContext) -> pd.DataFrame:
    columns = [
        "purchase_month",
        "month_label",
        "total_orders",
        "delivered_orders",
        "canceled_orders",
        "valid_orders",
        "revenue",
        "gross_revenue",
        "items",
        "orders_with_items",
        "valid_orders_with_items",
        "aov",
        "mom_growth",
        "cancellation_rate",
    ]
    if ctx.orders.empty:
        return _empty(columns)

    orders = ctx.orders
    order_agg = (
        orders.groupby("purchase_month", as_index=False)
        .agg(
            total_orders=("order_id", "nunique"),
            delivered_orders=("is_delivered", "sum"),
            canceled_orders=("is_canceled", "sum"),
            valid_orders=("is_valid_sale", "sum"),
        )
    )
    valid_orders = orders[orders["is_valid_sale"]]
    items = ctx.valid_items
    if not items.empty:
        item_agg = items.groupby("purchase_month", as_index=False).agg(
            revenue=("price", "sum"),
            gross_revenue=("gross_value", "sum"),
            items=("order_item_id", "size"),
            orders_with_items=("order_id", "nunique"),
        )
    else:
        item_agg = _empty(["purchase_month", "revenue", "gross_revenue", "items", "orders_with_items"])
    if not valid_orders.empty:
        with_items = (
            valid_orders[valid_orders["item_count"].gt(0)]
            .groupby("purchase_month", as_index=False)["order_id"]
            .nunique()
            .rename(columns={"order_id": "valid_orders_with_items"})
        )
    else:
        with_items = _empty(["purchase_month", "valid_orders_with_items"])

    monthly = order_agg.merge(item_agg, on="purchase_month", how="outer")
    monthly = monthly.merge(with_items, on="purchase_month", how="outer")
    months = _month_range(orders["purchase_month"])
    monthly = _fill_months(
        monthly,
        months,
        [
            "total_orders",
            "delivered_orders",
            "canceled_orders",
            "valid_orders",
            "revenue",
            "gross_revenue",
            "items",
            "orders_with_items",
            "valid_orders_with_items",
        ],
    )
    monthly["aov"] = monthly.apply(
        lambda row: safe_div(row["revenue"], row["valid_orders_with_items"]), axis=1
    )
    previous_revenue = monthly["revenue"].shift(1)
    monthly["mom_growth"] = (
        (monthly["revenue"] - previous_revenue) / previous_revenue.replace(0, np.nan) * 100
    ).replace([np.inf, -np.inf], np.nan)
    monthly["cancellation_rate"] = monthly.apply(
        lambda row: pct(row["canceled_orders"], row["total_orders"]), axis=1
    )
    monthly["month_label"] = pd.to_datetime(monthly["purchase_month"]).dt.strftime("%b %Y")
    for column in [
        "total_orders",
        "delivered_orders",
        "canceled_orders",
        "valid_orders",
        "items",
        "orders_with_items",
        "valid_orders_with_items",
    ]:
        monthly[column] = monthly[column].round().astype(int)
    return monthly[columns]


def category_performance(ctx: AnalysisContext) -> pd.DataFrame:
    columns = [
        "category",
        "revenue",
        "gross_revenue",
        "items",
        "orders",
        "products",
        "sellers",
        "avg_price",
        "revenue_share",
        "review_count",
        "avg_review",
        "delivered_orders",
        "late_rate",
    ]
    items = ctx.valid_items
    if items.empty:
        return _empty(columns)
    grouped = (
        items.groupby("category", as_index=False)
        .agg(
            revenue=("price", "sum"),
            gross_revenue=("gross_value", "sum"),
            items=("order_item_id", "size"),
            orders=("order_id", "nunique"),
            products=("product_id", "nunique"),
            sellers=("seller_id", "nunique"),
        )
    )
    grouped["avg_price"] = grouped["revenue"] / grouped["items"].replace(0, np.nan)
    total_revenue = grouped["revenue"].sum()
    grouped["revenue_share"] = grouped["revenue"].apply(lambda value: pct(value, total_revenue))

    pairs = items[["category", "order_id"]].drop_duplicates()
    order_info = ctx.orders[
        ["order_id", "review_score", "is_delivered", "has_delivery_dates", "is_late"]
    ]
    pair_info = pairs.merge(order_info, on="order_id", how="left")
    review_stats = (
        pair_info[pair_info["review_score"].between(1, 5)]
        .groupby("category", as_index=False)
        .agg(review_count=("review_score", "size"), avg_review=("review_score", "mean"))
    )
    delivery_info = pair_info[pair_info["is_delivered"] & pair_info["has_delivery_dates"]]
    late_stats = (
        delivery_info.groupby("category", as_index=False)
        .agg(delivered_orders=("order_id", "size"), late_orders=("is_late", "sum"))
        .assign(late_rate=lambda frame: frame.apply(
            lambda row: pct(row["late_orders"], row["delivered_orders"]), axis=1
        ))
        .drop(columns=["late_orders"])
    )
    grouped = grouped.merge(review_stats, on="category", how="left").merge(
        late_stats, on="category", how="left"
    )
    grouped["review_count"] = grouped["review_count"].fillna(0).astype(int)
    grouped["delivered_orders"] = grouped["delivered_orders"].fillna(0).astype(int)
    grouped["late_rate"] = grouped["late_rate"].fillna(0.0)
    return grouped.sort_values("revenue", ascending=False)[columns].reset_index(drop=True)


def state_performance(ctx: AnalysisContext) -> pd.DataFrame:
    columns = [
        "customer_state",
        "state_name",
        "revenue",
        "gross_revenue",
        "items",
        "orders",
        "orders_with_items",
        "avg_order_value",
        "revenue_share",
        "delivered_orders",
        "late_rate",
        "avg_review",
    ]
    items = ctx.valid_items
    if ctx.orders.empty:
        return _empty(columns)
    orders = ctx.orders
    order_stats = (
        orders.groupby("customer_state", as_index=False)
        .agg(
            orders=("order_id", "nunique"),
            delivered_orders=("is_delivered", "sum"),
        )
    )
    valid_with_items = (
        orders[orders["is_valid_sale"] & orders["item_count"].gt(0)]
        .groupby("customer_state", as_index=False)["order_id"]
        .nunique()
        .rename(columns={"order_id": "orders_with_items"})
    )
    order_stats = order_stats.merge(valid_with_items, on="customer_state", how="left")
    order_stats["orders_with_items"] = order_stats["orders_with_items"].fillna(0).astype(int)
    if not items.empty:
        revenue_stats = (
            items.groupby("customer_state", as_index=False)
            .agg(
                revenue=("price", "sum"),
                gross_revenue=("gross_value", "sum"),
                items=("order_item_id", "size"),
            )
        )
    else:
        revenue_stats = _empty(["customer_state", "revenue", "gross_revenue", "items"])
    reviews = (
        orders[orders["review_score"].between(1, 5)]
        .groupby("customer_state", as_index=False)["review_score"]
        .mean()
        .rename(columns={"review_score": "avg_review"})
    )
    delivery = orders[orders["is_delivered"] & orders["has_delivery_dates"]]
    late = (
        delivery.groupby("customer_state", as_index=False)
        .agg(delivered_valid=("order_id", "size"), late_orders=("is_late", "sum"))
        .assign(late_rate=lambda frame: frame.apply(
            lambda row: pct(row["late_orders"], row["delivered_valid"]), axis=1
        ))
        .drop(columns=["late_orders", "delivered_valid"])
    )
    grouped = order_stats.merge(revenue_stats, on="customer_state", how="left")
    grouped = grouped.merge(reviews, on="customer_state", how="left").merge(
        late, on="customer_state", how="left"
    )
    for column in ["revenue", "gross_revenue", "items"]:
        grouped[column] = grouped[column].fillna(0)
    grouped["late_rate"] = grouped["late_rate"].fillna(0.0)
    total_revenue = grouped["revenue"].sum()
    grouped["revenue_share"] = grouped["revenue"].apply(lambda value: pct(value, total_revenue))
    grouped["avg_order_value"] = grouped.apply(
        lambda row: safe_div(row["revenue"], row["orders_with_items"]), axis=1
    )
    grouped["state_name"] = grouped["customer_state"].map(STATE_NAMES).fillna(grouped["customer_state"])
    return grouped.sort_values("revenue", ascending=False)[columns].reset_index(drop=True)


def monthly_category_trend(ctx: AnalysisContext, top_n: int = 6) -> tuple[pd.DataFrame, list[str]]:
    """Revenue by month for the top categories, with a consolidated 'Other' series."""
    items = ctx.valid_items
    if items.empty:
        return _empty(["purchase_month", "month_label"]), []
    totals = items.groupby("category")["price"].sum().sort_values(ascending=False)
    top_categories = totals.head(top_n).index.tolist()
    grouped = (
        items.assign(
            category_group=np.where(items["category"].isin(top_categories), items["category"], "Other")
        )
        .groupby(["purchase_month", "category_group"], as_index=False)["price"]
        .sum()
        .pivot(index="purchase_month", columns="category_group", values="price")
        .fillna(0)
    )
    months = _month_range(ctx.orders["purchase_month"])
    grouped = grouped.reindex(months, fill_value=0)
    grouped.index.name = "purchase_month"
    grouped = grouped.reset_index()
    grouped["month_label"] = pd.to_datetime(grouped["purchase_month"]).dt.strftime("%b %Y")
    ordered = [category for category in top_categories if category in grouped.columns]
    if "Other" in grouped.columns:
        ordered.append("Other")
    return grouped, ordered


# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------
def _quantile_score(series: pd.Series, higher_is_better: bool = True, buckets: int = 5) -> pd.Series:
    """Rank-based 1..5 score that tolerates ties and small samples."""
    if len(series) <= 1 or series.nunique(dropna=True) <= 1:
        return pd.Series(3, index=series.index, dtype="int64")
    percentile = series.rank(method="average", pct=True, ascending=higher_is_better)
    return np.clip(np.ceil(percentile * buckets), 1, buckets).astype(int)


def _frequency_score(frequency: pd.Series) -> pd.Series:
    """Score raw purchase counts on an interpretable 1..5 scale.

    Quantile scores are unhelpful in this dataset because roughly 97% of
    customers placed exactly one order. Mapping absolute frequencies keeps the
    repeat-customer segments meaningful.
    """
    values = pd.to_numeric(frequency, errors="coerce").fillna(1)
    return pd.cut(
        values,
        bins=[0, 1, 2, 4, 7, np.inf],
        labels=[1, 2, 3, 4, 5],
        include_lowest=True,
        right=True,
    ).astype(int)


def _segment_customers(frame: pd.DataFrame) -> pd.Series:
    r = frame["r_score"]
    f = frame["f_score"]
    m = frame["m_score"]
    conditions = [
        (r >= 4) & (f >= 4) & (m >= 4),
        (r >= 3) & (f >= 3),
        (r >= 4) & (f == 1),
        (r >= 3) & (f == 1),
        (r >= 3) & (f >= 2),
        (r <= 2) & (f >= 3),
        (r <= 2) & (f == 2),
        (r <= 2) & (f == 1),
    ]
    choices = [
        "Champions",
        "Loyal customers",
        "New customers",
        "Promising",
        "Potential loyalists",
        "At risk",
        "Hibernating",
        "Lost",
    ]
    return pd.Series(
        np.select(conditions, choices, default="Needs attention"),
        index=frame.index,
        dtype="object",
    )


def customer_frame(ctx: AnalysisContext) -> pd.DataFrame:
    columns = [
        "customer_unique_id",
        "customer_state",
        "customer_city",
        "frequency",
        "monetary",
        "items",
        "avg_order_value",
        "first_purchase",
        "last_purchase",
        "recency_days",
        "r_score",
        "f_score",
        "m_score",
        "segment",
        "is_repeat",
    ]
    orders = ctx.valid_orders
    if orders.empty:
        return _empty(columns)
    base = orders.sort_values("purchase_ts")
    grouped = (
        base.groupby("customer_unique_id", as_index=False)
        .agg(
            customer_state=("customer_state", "last"),
            customer_city=("customer_city", "last"),
            frequency=("order_id", "nunique"),
            monetary=("item_revenue", "sum"),
            items=("item_count", "sum"),
            first_purchase=("purchase_ts", "min"),
            last_purchase=("purchase_ts", "max"),
        )
    )
    snapshot = base["purchase_ts"].max()
    grouped["recency_days"] = (snapshot - grouped["last_purchase"]).dt.days.clip(lower=0)
    grouped["avg_order_value"] = grouped.apply(
        lambda row: safe_div(row["monetary"], row["frequency"]), axis=1
    )
    grouped["r_score"] = _quantile_score(grouped["recency_days"], higher_is_better=False)
    grouped["f_score"] = _frequency_score(grouped["frequency"])
    grouped["m_score"] = _quantile_score(grouped["monetary"], higher_is_better=True)
    grouped["segment"] = _segment_customers(grouped)
    grouped["is_repeat"] = grouped["frequency"].gt(1)
    return grouped.sort_values("monetary", ascending=False)[columns].reset_index(drop=True)


def segment_summary(customers: pd.DataFrame) -> pd.DataFrame:
    columns = ["segment", "customers", "customer_share", "revenue", "revenue_share", "avg_monetary"]
    if customers.empty:
        return _empty(columns)
    total_customers = len(customers)
    total_revenue = customers["monetary"].sum()
    grouped = (
        customers.groupby("segment", as_index=False)
        .agg(customers=("customer_unique_id", "nunique"), revenue=("monetary", "sum"))
        .assign(
            customer_share=lambda frame: frame["customers"].apply(
                lambda value: pct(value, total_customers)
            ),
            revenue_share=lambda frame: frame["revenue"].apply(
                lambda value: pct(value, total_revenue)
            ),
            avg_monetary=lambda frame: frame["revenue"] / frame["customers"].replace(0, np.nan),
        )
        .sort_values("revenue", ascending=False)
    )
    return grouped[columns].reset_index(drop=True)


def purchase_frequency(customers: pd.DataFrame) -> pd.DataFrame:
    columns = ["frequency_bucket", "customers", "share"]
    if customers.empty:
        return _empty(columns)
    frequency = customers["frequency"].clip(upper=5)
    counts = frequency.value_counts().sort_index()
    labels = {1: "1 order", 2: "2 orders", 3: "3 orders", 4: "4 orders", 5: "5+ orders"}
    total = int(counts.sum())
    frame = pd.DataFrame(
        {
            "frequency_bucket": [labels.get(int(index), f"{index} orders") for index in counts.index],
            "customers": counts.values.astype(int),
        }
    )
    frame["share"] = frame["customers"].apply(lambda value: pct(value, total))
    return frame[columns]


def new_returning_monthly(ctx: AnalysisContext) -> pd.DataFrame:
    columns = ["purchase_month", "month_label", "new_customers", "returning_customers", "total_customers"]
    orders = ctx.valid_orders
    if orders.empty:
        return _empty(columns)
    base = orders.dropna(subset=["purchase_month", "customer_unique_id"]).copy()
    if base.empty:
        return _empty(columns)
    first_month = base.groupby("customer_unique_id")["purchase_month"].min().rename("first_month")
    base = base.merge(first_month, on="customer_unique_id", how="left")
    base["customer_type"] = np.where(
        base["purchase_month"].eq(base["first_month"]), "new_customers", "returning_customers"
    )
    monthly = (
        base.groupby(["purchase_month", "customer_type"])["customer_unique_id"]
        .nunique()
        .unstack(fill_value=0)
        .reset_index()
    )
    for column in ["new_customers", "returning_customers"]:
        if column not in monthly.columns:
            monthly[column] = 0
    months = _month_range(base["purchase_month"])
    monthly = _fill_months(monthly, months, ["new_customers", "returning_customers"])
    monthly["total_customers"] = monthly["new_customers"] + monthly["returning_customers"]
    monthly["month_label"] = pd.to_datetime(monthly["purchase_month"]).dt.strftime("%b %Y")
    return monthly[columns]


def customer_state_summary(customers: pd.DataFrame) -> pd.DataFrame:
    columns = ["customer_state", "state_name", "customers", "revenue", "repeat_rate"]
    if customers.empty:
        return _empty(columns)
    grouped = (
        customers.groupby("customer_state", as_index=False)
        .agg(customers=("customer_unique_id", "nunique"), revenue=("monetary", "sum"), repeats=("is_repeat", "sum"))
        .assign(
            repeat_rate=lambda frame: frame.apply(
                lambda row: pct(row["repeats"], row["customers"]), axis=1
            ),
            state_name=lambda frame: frame["customer_state"].map(STATE_NAMES).fillna(frame["customer_state"]),
        )
        .sort_values("customers", ascending=False)
    )
    return grouped[columns].reset_index(drop=True)


# ---------------------------------------------------------------------------
# Products and sellers
# ---------------------------------------------------------------------------
def top_products(ctx: AnalysisContext, limit: int = 25) -> pd.DataFrame:
    columns = [
        "product_id",
        "category",
        "revenue",
        "units",
        "orders",
        "avg_price",
        "sellers",
        "first_sale",
        "last_sale",
    ]
    items = ctx.valid_items
    if items.empty:
        return _empty(columns)
    grouped = (
        items.groupby("product_id", as_index=False)
        .agg(
            category=("category", "first"),
            revenue=("price", "sum"),
            units=("order_item_id", "size"),
            orders=("order_id", "nunique"),
            avg_price=("price", "mean"),
            sellers=("seller_id", "nunique"),
            first_sale=("purchase_date", "min"),
            last_sale=("purchase_date", "max"),
        )
        .sort_values("revenue", ascending=False)
        .head(limit)
    )
    return grouped[columns].reset_index(drop=True)


def seller_performance(ctx: AnalysisContext) -> pd.DataFrame:
    columns = [
        "seller_id",
        "seller_city",
        "seller_state",
        "revenue",
        "items",
        "orders",
        "products",
        "avg_item_price",
        "revenue_share",
        "delivered_orders",
        "late_rate",
    ]
    items = ctx.valid_items
    if items.empty:
        return _empty(columns)
    grouped = (
        items.groupby("seller_id", as_index=False)
        .agg(
            seller_city=("seller_city", "first"),
            seller_state=("seller_state", "first"),
            revenue=("price", "sum"),
            items=("order_item_id", "size"),
            orders=("order_id", "nunique"),
            products=("product_id", "nunique"),
        )
    )
    grouped["avg_item_price"] = grouped["revenue"] / grouped["items"].replace(0, np.nan)
    total_revenue = grouped["revenue"].sum()
    grouped["revenue_share"] = grouped["revenue"].apply(lambda value: pct(value, total_revenue))

    pairs = items[["seller_id", "order_id"]].drop_duplicates()
    pair_info = pairs.merge(
        ctx.orders[["order_id", "is_delivered", "has_delivery_dates", "is_late"]],
        on="order_id",
        how="left",
    )
    delivery = pair_info[pair_info["is_delivered"] & pair_info["has_delivery_dates"]]
    late = (
        delivery.groupby("seller_id", as_index=False)
        .agg(delivered_orders=("order_id", "size"), late_orders=("is_late", "sum"))
        .assign(late_rate=lambda frame: frame.apply(
            lambda row: pct(row["late_orders"], row["delivered_orders"]), axis=1
        ))
        .drop(columns=["late_orders"])
    )
    grouped = grouped.merge(late, on="seller_id", how="left")
    grouped["delivered_orders"] = grouped["delivered_orders"].fillna(0).astype(int)
    grouped["late_rate"] = grouped["late_rate"].fillna(0.0)
    return grouped.sort_values("revenue", ascending=False)[columns].reset_index(drop=True)


def seller_state_summary(ctx: AnalysisContext) -> pd.DataFrame:
    columns = ["seller_state", "state_name", "sellers", "revenue", "items", "orders"]
    items = ctx.valid_items
    if items.empty:
        return _empty(columns)
    grouped = (
        items.groupby("seller_state", as_index=False)
        .agg(
            sellers=("seller_id", "nunique"),
            revenue=("price", "sum"),
            items=("order_item_id", "size"),
            orders=("order_id", "nunique"),
        )
        .assign(state_name=lambda frame: frame["seller_state"].map(STATE_NAMES).fillna(frame["seller_state"]))
        .sort_values("revenue", ascending=False)
    )
    return grouped[columns].reset_index(drop=True)


# ---------------------------------------------------------------------------
# Delivery
# ---------------------------------------------------------------------------
def delivery_metrics(ctx: AnalysisContext) -> dict[str, object]:
    orders = ctx.orders
    delivered = orders[orders["is_delivered"]] if not orders.empty else orders
    valid = (
        delivered[
            delivered["delivered_ts"].notna()
            & delivered["purchase_ts"].notna()
            & delivered["delivery_days"].ge(0)
        ]
        if not delivered.empty
        else delivered
    )
    estimate_valid = valid[valid["estimated_ts"].notna()] if not valid.empty else valid
    late = estimate_valid[estimate_valid["is_late"]] if not estimate_valid.empty else estimate_valid
    early = estimate_valid[estimate_valid["is_late"].eq(False)] if not estimate_valid.empty else estimate_valid
    days = valid["delivery_days"] if not valid.empty else pd.Series(dtype=float)
    avg_delay_late = (
        float(late["delay_days"].mean()) if not late.empty else float("nan")
    )
    avg_early = (
        float((-early["delay_days"]).clip(lower=0).mean()) if not early.empty else float("nan")
    )
    carrier_valid = valid[valid["carrier_days"].ge(0)] if not valid.empty else valid
    transit_valid = valid[valid["transit_days"].ge(0)] if not valid.empty else valid

    metrics: dict[str, object] = {
        "delivered_orders": int(len(delivered)),
        "delivered_with_valid_dates": int(len(valid)),
        "delivered_missing_delivery_date": int(
            delivered["delivered_ts"].isna().sum() if not delivered.empty else 0
        ),
        "avg_delivery_days": float(days.mean()) if len(days) else float("nan"),
        "median_delivery_days": float(days.median()) if len(days) else float("nan"),
        "p90_delivery_days": float(days.quantile(0.9)) if len(days) else float("nan"),
        "avg_estimated_days": (
            float(valid["estimated_days"].mean()) if not valid.empty else float("nan")
        ),
        "late_orders": int(len(late)),
        "on_time_orders": int(len(early)),
        "late_rate": pct(len(late), len(estimate_valid)),
        "on_time_rate": pct(len(early), len(estimate_valid)),
        "avg_late_days": avg_delay_late,
        "avg_early_days": avg_early,
        "avg_carrier_days": (
            float(carrier_valid["carrier_days"].mean()) if not carrier_valid.empty else float("nan")
        ),
        "avg_transit_days": (
            float(transit_valid["transit_days"].mean()) if not transit_valid.empty else float("nan")
        ),
        "delivery_coverage": pct(len(valid), len(delivered)),
    }

    if not valid.empty:
        monthly = (
            valid.groupby("purchase_month", as_index=False)
            .agg(
                delivered=("order_id", "size"),
                avg_delivery_days=("delivery_days", "mean"),
                median_delivery_days=("delivery_days", "median"),
                avg_carrier_days=("carrier_days", "mean"),
                avg_transit_days=("transit_days", "mean"),
            )
        )
        late_monthly = (
            estimate_valid.groupby("purchase_month", as_index=False)
            .agg(late_orders=("is_late", "sum"), estimated_orders=("order_id", "size"))
            .assign(late_rate=lambda frame: frame.apply(
                lambda row: pct(row["late_orders"], row["estimated_orders"]), axis=1
            ))
        )
        monthly = monthly.merge(late_monthly, on="purchase_month", how="left")
        monthly = _fill_months(
            monthly,
            _month_range(valid["purchase_month"]),
            [
                "delivered",
                "avg_delivery_days",
                "median_delivery_days",
                "avg_carrier_days",
                "avg_transit_days",
                "late_orders",
                "estimated_orders",
                "late_rate",
            ],
        )
        monthly["month_label"] = pd.to_datetime(monthly["purchase_month"]).dt.strftime("%b %Y")
    else:
        monthly = _empty(
            [
                "purchase_month",
                "month_label",
                "delivered",
                "avg_delivery_days",
                "median_delivery_days",
                "avg_carrier_days",
                "avg_transit_days",
                "late_orders",
                "estimated_orders",
                "late_rate",
            ]
        )
    metrics["monthly"] = monthly

    if not estimate_valid.empty:
        state = (
            estimate_valid.groupby("customer_state", as_index=False)
            .agg(delivered=("order_id", "size"), late_orders=("is_late", "sum"))
            .assign(late_rate=lambda frame: frame.apply(
                lambda row: pct(row["late_orders"], row["delivered"]), axis=1
            ))
            .sort_values("late_rate", ascending=False)
        )
        state["state_name"] = state["customer_state"].map(STATE_NAMES).fillna(state["customer_state"])
    else:
        state = _empty(["customer_state", "state_name", "delivered", "late_orders", "late_rate"])
    metrics["late_by_state"] = state

    if not valid.empty:
        stage = (
            valid.groupby("purchase_month", as_index=False)
            .agg(
                avg_carrier_days=("carrier_days", "mean"),
                avg_transit_days=("transit_days", "mean"),
                avg_total_days=("delivery_days", "mean"),
            )
            .sort_values("purchase_month")
        )
        stage["month_label"] = pd.to_datetime(stage["purchase_month"]).dt.strftime("%b %Y")
    else:
        stage = _empty(
            ["purchase_month", "month_label", "avg_carrier_days", "avg_transit_days", "avg_total_days"]
        )
    metrics["stage_monthly"] = stage
    return metrics


def delivery_by_category(ctx: AnalysisContext, min_orders: int = 30) -> pd.DataFrame:
    columns = ["category", "delivered_orders", "avg_delivery_days", "late_rate"]
    delivered = ctx.orders[ctx.orders["is_delivered"] & ctx.orders["has_delivery_dates"]]
    if delivered.empty:
        return _empty(columns)
    pairs = (
        ctx.items[ctx.items["order_id"].isin(delivered["order_id"])][["category", "order_id"]]
        .drop_duplicates()
        .merge(delivered[["order_id", "delivery_days", "is_late"]], on="order_id", how="inner")
    )
    if pairs.empty:
        return _empty(columns)
    grouped = (
        pairs.groupby("category", as_index=False)
        .agg(
            delivered_orders=("order_id", "size"),
            avg_delivery_days=("delivery_days", "mean"),
            late_orders=("is_late", "sum"),
        )
        .assign(late_rate=lambda frame: frame.apply(
            lambda row: pct(row["late_orders"], row["delivered_orders"]), axis=1
        ))
    )
    grouped = grouped[grouped["delivered_orders"] >= min_orders]
    return grouped.sort_values("late_rate", ascending=False)[columns].reset_index(drop=True)


# ---------------------------------------------------------------------------
# Satisfaction
# ---------------------------------------------------------------------------
def satisfaction_metrics(ctx: AnalysisContext) -> dict[str, object]:
    reviews = ctx.reviews
    if reviews.empty:
        empty_dist = _empty(["review_score", "reviews", "share"])
        empty_monthly = _empty(["purchase_month", "month_label", "reviews", "avg_score"])
        empty_buckets = _empty(["delay_bucket", "reviews", "avg_score", "share"])
        return {
            "review_count": 0,
            "avg_score": float("nan"),
            "median_score": float("nan"),
            "five_star_rate": 0.0,
            "low_score_rate": 0.0,
            "review_coverage": 0.0,
            "distribution": empty_dist,
            "monthly": empty_monthly,
            "delay_buckets": empty_buckets,
            "late_avg_score": float("nan"),
            "on_time_avg_score": float("nan"),
            "score_gap": float("nan"),
            "correlation": float("nan"),
            "late_reviews": 0,
            "on_time_reviews": 0,
        }
    valid = reviews[reviews["review_score"].between(1, 5)].copy()
    if valid.empty:
        return {
            "review_count": 0,
            "avg_score": float("nan"),
            "median_score": float("nan"),
            "five_star_rate": 0.0,
            "low_score_rate": 0.0,
            "review_coverage": 0.0,
            "distribution": _empty(["review_score", "reviews", "share"]),
            "monthly": _empty(["purchase_month", "month_label", "reviews", "avg_score"]),
            "delay_buckets": _empty(["delay_bucket", "reviews", "avg_score", "share"]),
            "late_avg_score": float("nan"),
            "on_time_avg_score": float("nan"),
            "score_gap": float("nan"),
            "correlation": float("nan"),
            "late_reviews": 0,
            "on_time_reviews": 0,
        }
    count = len(valid)
    distribution = (
        valid.groupby("review_score", as_index=False)
        .agg(reviews=("review_score", "size"))
        .sort_values("review_score")
    )
    distribution["share"] = distribution["reviews"].apply(lambda value: pct(value, count))
    monthly = (
        valid.groupby("purchase_month", as_index=False)
        .agg(reviews=("review_score", "size"), avg_score=("review_score", "mean"))
        .sort_values("purchase_month")
    )
    monthly["month_label"] = pd.to_datetime(monthly["purchase_month"]).dt.strftime("%b %Y")

    delivered = valid[valid["is_delivered"] & valid["has_delivery_dates"]].copy()
    delivered["delay_bucket"] = pd.cut(
        delivered["delay_days"],
        bins=[-np.inf, 0, 3, 7, 14, np.inf],
        labels=["On time / early", "1–3 days late", "4–7 days late", "8–14 days late", "15+ days late"],
        right=True,
    )
    buckets = (
        delivered.groupby("delay_bucket", observed=False, as_index=False)
        .agg(reviews=("review_score", "size"), avg_score=("review_score", "mean"))
    )
    buckets["delay_bucket"] = buckets["delay_bucket"].astype(str)
    buckets["share"] = buckets["reviews"].apply(lambda value: pct(value, len(delivered)))
    late_scores = delivered.loc[delivered["is_late"], "review_score"]
    on_time_scores = delivered.loc[delivered["is_late"].eq(False), "review_score"]
    correlation = float("nan")
    if len(delivered) > 2:
        ranked = delivered[["delay_days", "review_score"]].rank().corr().iloc[0, 1]
        correlation = float(ranked) if pd.notna(ranked) else float("nan")

    return {
        "review_count": count,
        "avg_score": float(valid["review_score"].mean()),
        "median_score": float(valid["review_score"].median()),
        "five_star_rate": pct(int((valid["review_score"] == 5).sum()), count),
        "low_score_rate": pct(int(valid["review_score"].isin([1, 2]).sum()), count),
        "review_coverage": pct(count, len(ctx.orders)),
        "distribution": distribution.reset_index(drop=True),
        "monthly": monthly.reset_index(drop=True),
        "delay_buckets": buckets.reset_index(drop=True),
        "late_avg_score": float(late_scores.mean()) if len(late_scores) else float("nan"),
        "on_time_avg_score": float(on_time_scores.mean()) if len(on_time_scores) else float("nan"),
        "score_gap": (
            float(on_time_scores.mean() - late_scores.mean())
            if len(late_scores) and len(on_time_scores)
            else float("nan")
        ),
        "correlation": correlation,
        "late_reviews": int(len(late_scores)),
        "on_time_reviews": int(len(on_time_scores)),
    }


def category_reviews(ctx: AnalysisContext, min_reviews: int = 30) -> pd.DataFrame:
    columns = ["category", "reviews", "avg_score", "five_star_rate", "low_score_rate"]
    items = ctx.valid_items
    if items.empty or ctx.reviews.empty:
        return _empty(columns)
    pairs = items[["category", "order_id"]].drop_duplicates()
    merged = pairs.merge(
        ctx.reviews[["order_id", "review_score"]], on="order_id", how="inner"
    )
    merged = merged[merged["review_score"].between(1, 5)]
    if merged.empty:
        return _empty(columns)
    grouped = (
        merged.groupby("category", as_index=False)
        .agg(
            reviews=("review_score", "size"),
            avg_score=("review_score", "mean"),
            five_star=("review_score", lambda values: int((values == 5).sum())),
            low=("review_score", lambda values: int(values.isin([1, 2]).sum())),
        )
        .assign(
            five_star_rate=lambda frame: frame.apply(
                lambda row: pct(row["five_star"], row["reviews"]), axis=1
            ),
            low_score_rate=lambda frame: frame.apply(
                lambda row: pct(row["low"], row["reviews"]), axis=1
            ),
        )
    )
    grouped = grouped[grouped["reviews"] >= min_reviews]
    return grouped.sort_values("avg_score", ascending=False)[columns].reset_index(drop=True)


# ---------------------------------------------------------------------------
# Payments
# ---------------------------------------------------------------------------
def payment_metrics(ctx: AnalysisContext) -> dict[str, object]:
    payments = ctx.payments
    if payments.empty:
        return {
            "payment_total": 0.0,
            "orders_with_payment": 0,
            "avg_payment": 0.0,
            "avg_installments": 0.0,
            "max_installments": 0,
            "installment_order_share": 0.0,
            "top_method": "—",
            "top_method_value": 0.0,
            "methods": _empty(["payment_type", "records", "orders", "value", "avg_value", "share_value", "avg_installments"]),
            "monthly": _empty(["purchase_month", "month_label", "value", "orders", "records"]),
            "method_monthly": _empty(["purchase_month", "month_label"]),
            "installments": _empty(["installments", "orders", "share", "avg_value"]),
            "reconciliation": None,
            "zero_value_records": 0,
        }

    methods = (
        payments.groupby("payment_type", as_index=False)
        .agg(
            records=("payment_value", "size"),
            orders=("order_id", "nunique"),
            value=("payment_value", "sum"),
            avg_value=("payment_value", "mean"),
            avg_installments=("payment_installments", "mean"),
        )
        .sort_values("value", ascending=False)
    )
    total_value = methods["value"].sum()
    methods["share_value"] = methods["value"].apply(lambda value: pct(value, total_value))
    top = methods.iloc[0] if not methods.empty else None

    order_level = ctx.orders[ctx.orders["payment_records"].gt(0)]
    if not order_level.empty:
        order_installments = order_level["max_installments"].clip(lower=0)
        installment_orders = int(order_installments.gt(1).sum())
        avg_max_installments = float(order_installments.mean())
        max_installments = int(order_installments.max())
        installment_share = pct(installment_orders, len(order_level))
        histogram = (
            order_installments.value_counts().sort_index().rename_axis("installments").reset_index(name="orders")
        )
        histogram["share"] = histogram["orders"].apply(lambda value: pct(value, len(order_level)))
        avg_value = (
            order_level.groupby("max_installments")["payment_value"]
            .mean()
            .reset_index()
            .rename(columns={"max_installments": "installments", "payment_value": "avg_value"})
        )
        histogram = histogram.merge(avg_value, on="installments", how="left")
    else:
        installment_orders = 0
        avg_max_installments = 0.0
        max_installments = 0
        installment_share = 0.0
        histogram = _empty(["installments", "orders", "share", "avg_value"])

    monthly = (
        payments.groupby("purchase_month", as_index=False)
        .agg(
            value=("payment_value", "sum"),
            orders=("order_id", "nunique"),
            records=("payment_value", "size"),
        )
        .sort_values("purchase_month")
    )
    monthly = _fill_months(
        monthly,
        _month_range(payments["purchase_month"]),
        ["value", "orders", "records"],
    )
    monthly["month_label"] = pd.to_datetime(monthly["purchase_month"]).dt.strftime("%b %Y")

    top_methods = methods.head(5)["payment_type"].tolist()
    method_monthly_source = payments[payments["payment_type"].isin(top_methods)]
    method_monthly = (
        method_monthly_source.groupby(["purchase_month", "payment_type"], as_index=False)["payment_value"]
        .sum()
        .pivot(index="purchase_month", columns="payment_type", values="payment_value")
        .fillna(0)
        .reindex(_month_range(payments["purchase_month"]), fill_value=0)
        .reset_index()
    )
    method_monthly["month_label"] = pd.to_datetime(method_monthly["purchase_month"]).dt.strftime("%b %Y")

    reconciliation = None
    if not ctx.filters.categories:
        candidate = ctx.orders[ctx.orders["has_items"] & ctx.orders["payment_records"].gt(0)].copy()
        if not candidate.empty:
            candidate["payment_difference"] = candidate["gross_revenue"] - candidate["payment_value"]
            mismatches = candidate[candidate["payment_difference"].abs().gt(0.01)]
            reconciliation = {
                "orders_checked": int(len(candidate)),
                "mismatches": int(len(mismatches)),
                "mismatch_rate": pct(len(mismatches), len(candidate)),
                "absolute_difference": float(mismatches["payment_difference"].abs().sum()),
            }

    zero_records = int(payments["payment_value"].le(0).sum())

    return {
        "payment_total": float(total_value),
        "orders_with_payment": int(payments["order_id"].nunique()),
        "avg_payment": safe_div(total_value, payments["order_id"].nunique()),
        "avg_installments": avg_max_installments,
        "max_installments": max_installments,
        "installment_order_share": installment_share,
        "installment_orders": installment_orders,
        "top_method": str(top["payment_type"]) if top is not None else "—",
        "top_method_value": float(top["value"]) if top is not None else 0.0,
        "methods": methods.reset_index(drop=True),
        "monthly": monthly.reset_index(drop=True),
        "method_monthly": method_monthly.reset_index(drop=True),
        "installments": histogram.reset_index(drop=True),
        "reconciliation": reconciliation,
        "zero_value_records": zero_records,
    }
