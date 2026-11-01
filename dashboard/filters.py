"""Interactive filter model and safe order-level context construction."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

import pandas as pd

from .config import STATE_NAMES
from .data import item_aggregates, payment_aggregates


@dataclass(frozen=True)
class FilterSelection:
    """User-selected filters shared across all pages."""

    start_date: date | datetime | None = None
    end_date: date | datetime | None = None
    statuses: tuple[str, ...] = ()
    states: tuple[str, ...] = ()
    categories: tuple[str, ...] = ()

    @property
    def is_empty(self) -> bool:
        return not (self.statuses or self.states or self.categories)


@dataclass
class AnalysisContext:
    """Order, item, payment and review frames after filters are applied."""

    orders: pd.DataFrame
    items: pd.DataFrame
    payments: pd.DataFrame
    reviews: pd.DataFrame
    filters: FilterSelection
    total_orders_unfiltered: int = 0
    source_path: str = ""
    notes: list[str] = field(default_factory=list)

    @property
    def has_orders(self) -> bool:
        return not self.orders.empty

    @property
    def has_items(self) -> bool:
        return not self.items.empty

    @property
    def valid_orders(self) -> pd.DataFrame:
        return self.orders[self.orders["is_valid_sale"]]

    @property
    def valid_items(self) -> pd.DataFrame:
        """Items belonging to non-canceled, non-unavailable orders."""
        if "is_valid_sale" not in self.items.columns:
            return self.items
        return self.items[self.items["is_valid_sale"]]


def _to_timestamp(value: date | datetime | None, end: bool = False) -> pd.Timestamp | None:
    """Convert a calendar date to a timezone-naive, midnight-normalised timestamp."""
    if value is None:
        return None
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is not None:
        # Purchase timestamps in the dataset are timezone-naive. Convert any
        # aware widget value to UTC and drop the zone so comparisons stay valid.
        timestamp = timestamp.tz_convert("UTC").tz_localize(None)
    return timestamp.normalize()


def _ensure_columns(frame: pd.DataFrame, columns: dict[str, Any]) -> pd.DataFrame:
    for column, default in columns.items():
        if column not in frame.columns:
            frame[column] = default
    return frame


def _empty_context(data: dict[str, Any], filters: FilterSelection) -> AnalysisContext:
    orders = data["orders"].iloc[0:0].copy()
    orders = _ensure_columns(
        orders,
        {
            "item_revenue": 0.0,
            "freight_revenue": 0.0,
            "gross_revenue": 0.0,
            "item_count": 0,
            "product_count": 0,
            "seller_count": 0,
            "payment_value": 0.0,
            "payment_records": 0,
            "max_installments": 0,
            "primary_payment_type": "No payment",
            "payment_type_list": "",
            "review_score": float("nan"),
            "review_creation_date": pd.NaT,
            "review_answer_timestamp": pd.NaT,
            "has_items": False,
        },
    )
    items = data["items"].iloc[0:0].copy()
    payments = data["payments"].iloc[0:0].copy()
    reviews = data["reviews"].iloc[0:0].copy()
    return AnalysisContext(
        orders=orders,
        items=items,
        payments=payments,
        reviews=reviews,
        filters=filters,
        total_orders_unfiltered=int(data["orders"]["order_id"].nunique()),
        source_path=str(data.get("metadata", {}).get("db_path", "")),
        notes=list(data.get("notes", [])),
    )


def apply_filters(data: dict[str, Any], filters: FilterSelection) -> AnalysisContext:
    """Filter source data and build non-duplicated analysis frames.

    Key guarantee: item and payment rows are aggregated to one row per order
    *before* being joined to the order table. This prevents revenue, orders,
    customers and review counts from inflating due to one-to-many joins.
    """
    start = _to_timestamp(filters.start_date)
    end = _to_timestamp(filters.end_date, end=True)
    if start is not None and end is not None and start > end:
        raise ValueError("The start date must be before or equal to the end date.")

    orders = data["orders"].copy()

    if start is not None:
        orders = orders[orders["purchase_date"].ge(start)]
    if end is not None:
        orders = orders[orders["purchase_date"].le(end)]
    if filters.statuses:
        statuses = {status.lower() for status in filters.statuses}
        orders = orders[orders["order_status"].isin(statuses)]
    if filters.states:
        states = {state.upper() for state in filters.states}
        orders = orders[orders["customer_state"].isin(states)]
    if orders.empty:
        return _empty_context(data, filters)

    source_items = data["items"]
    items = source_items[source_items["order_id"].isin(orders["order_id"])].copy()

    if filters.categories:
        categories = set(filters.categories)
        items = items[items["category"].isin(categories)]
        if items.empty:
            return _empty_context(data, filters)
        # Keep only orders that actually contain one of the selected categories.
        orders = orders[orders["order_id"].isin(items["order_id"])]

    # Aggregate children to one row per order before merging.
    items_per_order = item_aggregates(items)
    payments_per_order = payment_aggregates(
        data["payments"][data["payments"]["order_id"].isin(orders["order_id"])]
    )
    reviews_latest = data["reviews"][data["reviews"]["order_id"].isin(orders["order_id"])].copy()

    orders = orders.merge(items_per_order, on="order_id", how="left")
    orders = _ensure_columns(
        orders,
        {
            "item_revenue": 0.0,
            "freight_revenue": 0.0,
            "gross_revenue": 0.0,
            "item_count": 0,
            "product_count": 0,
            "seller_count": 0,
        },
    )
    for column in [
        "item_revenue",
        "freight_revenue",
        "gross_revenue",
        "item_count",
        "product_count",
        "seller_count",
    ]:
        orders[column] = orders[column].fillna(0)
    orders["item_count"] = orders["item_count"].astype(int)
    orders["product_count"] = orders["product_count"].astype(int)
    orders["seller_count"] = orders["seller_count"].astype(int)
    orders["has_items"] = orders["item_count"].gt(0)

    orders = orders.merge(payments_per_order, on="order_id", how="left")
    orders = _ensure_columns(
        orders,
        {
            "payment_value": 0.0,
            "payment_records": 0,
            "max_installments": 0,
            "primary_payment_type": "No payment",
            "payment_type_list": "",
        },
    )
    orders["payment_value"] = orders["payment_value"].fillna(0.0)
    orders["payment_records"] = orders["payment_records"].fillna(0).astype(int)
    orders["max_installments"] = orders["max_installments"].fillna(0).astype(int)
    orders["primary_payment_type"] = orders["primary_payment_type"].fillna("No payment")
    orders["payment_type_list"] = orders["payment_type_list"].fillna("")

    review_columns = [
        "order_id",
        "review_score",
        "review_creation_date",
        "review_answer_timestamp",
    ]
    orders = orders.merge(reviews_latest[review_columns], on="order_id", how="left")
    orders = _ensure_columns(
        orders,
        {
            "review_score": float("nan"),
            "review_creation_date": pd.NaT,
            "review_answer_timestamp": pd.NaT,
        },
    )

    # Enrich item/payment/review rows with the order-level dimensions required by
    # page-level grouping. These additions do not multiply rows.
    order_dimensions = orders[
        [
            "order_id",
            "purchase_date",
            "purchase_month",
            "purchase_weekday",
            "order_status",
            "customer_state",
            "customer_unique_id",
            "is_valid_sale",
            "is_delivered",
            "has_delivery_dates",
            "is_late",
            "delivery_days",
            "delay_days",
        ]
    ]
    items = items.merge(order_dimensions, on="order_id", how="left")
    payments = data["payments"][data["payments"]["order_id"].isin(orders["order_id"])].copy()
    payments = payments.merge(order_dimensions, on="order_id", how="left")
    reviews = reviews_latest.merge(order_dimensions, on="order_id", how="left")

    notes = []
    if filters.categories:
        notes.append(
            "Category filter is active: revenue covers the selected categories only, while "
            "order counts include any order containing them."
        )
    if filters.statuses and "canceled" in {s.lower() for s in filters.statuses}:
        notes.append("Canceled orders are included by the status filter; revenue excludes them.")

    return AnalysisContext(
        orders=orders,
        items=items,
        payments=payments,
        reviews=reviews,
        filters=filters,
        total_orders_unfiltered=int(data["orders"]["order_id"].nunique()),
        source_path=str(data.get("metadata", {}).get("db_path", "")),
        notes=notes,
    )


def filter_options(data: dict[str, Any]) -> dict[str, Any]:
    """Build sidebar filter options and counts from the full dataset."""
    orders = data["orders"]
    items = data["items"]
    min_date = orders["purchase_date"].min()
    max_date = orders["purchase_date"].max()
    if pd.isna(min_date):
        min_date = pd.Timestamp("2016-01-01")
    if pd.isna(max_date):
        max_date = pd.Timestamp("2018-12-31")

    status_counts = orders["order_status"].value_counts().to_dict()
    state_counts = orders["customer_state"].value_counts().to_dict()
    category_counts = items["category"].value_counts().to_dict()

    states = sorted(
        state_counts,
        key=lambda state: (-int(state_counts[state]), state),
    )
    categories = sorted(
        category_counts,
        key=lambda category: (-int(category_counts[category]), category),
    )
    statuses = sorted(status_counts, key=lambda status: (-int(status_counts[status]), status))

    return {
        "min_date": pd.Timestamp(min_date).date(),
        "max_date": pd.Timestamp(max_date).date(),
        "status_counts": {key: int(value) for key, value in status_counts.items()},
        "state_counts": {key: int(value) for key, value in state_counts.items()},
        "category_counts": {key: int(value) for key, value in category_counts.items()},
        "statuses": statuses,
        "states": states,
        "categories": categories,
        "state_names": STATE_NAMES,
    }
