"""Data quality checks for the Olist source tables."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .config import SENTINEL_VALUES
from .formatting import pct

TABLE_LABELS = {
    "orders": "Orders",
    "items": "Order items",
    "payments": "Payments",
    "reviews_all": "Reviews (raw)",
    "customers": "Customers",
    "products": "Products",
    "sellers": "Sellers",
    "translation": "Category translation",
}

KEY_COLUMNS = {
    "orders": "order_id",
    "items": None,
    "payments": None,
    "reviews_all": "review_id",
    "customers": "customer_id",
    "products": "product_id",
    "sellers": "seller_id",
    "translation": None,
}


def _is_text(series: pd.Series) -> bool:
    return pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series)


def _missing_count(series: pd.Series) -> int:
    missing = series.isna()
    if _is_text(series):
        missing = missing | series.astype("string").str.strip().str.lower().isin(SENTINEL_VALUES)
    return int(missing.sum())


def _table_profile(name: str, frame: pd.DataFrame) -> dict[str, Any]:
    rows = len(frame)
    columns = len(frame.columns)
    missing_cells = int(sum(_missing_count(frame[column]) for column in frame.columns))
    duplicate_rows = int(frame.duplicated().sum())
    key = KEY_COLUMNS.get(name)
    duplicate_keys = 0
    if key and key in frame.columns:
        duplicate_keys = int(frame.duplicated(subset=[key]).sum())
    return {
        "table": TABLE_LABELS.get(name, name),
        "rows": rows,
        "columns": columns,
        "cells": rows * columns,
        "missing_cells": missing_cells,
        "missing_pct": pct(missing_cells, rows * columns),
        "duplicate_rows": duplicate_rows,
        "duplicate_keys": duplicate_keys,
    }


def _missing_details(data: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for name, label in TABLE_LABELS.items():
        frame = data[name]
        for column in frame.columns:
            missing = _missing_count(frame[column])
            if missing:
                rows.append(
                    {
                        "table": label,
                        "column": column,
                        "missing": missing,
                        "missing_pct": pct(missing, len(frame)),
                    }
                )
    return pd.DataFrame(rows, columns=["table", "column", "missing", "missing_pct"]).sort_values(
        ["table", "missing"], ascending=[True, False]
    )


def _invalid_dates(data: dict[str, Any]) -> pd.DataFrame:
    orders = data["orders"]
    reviews = data["reviews_all"]
    items = data["items"]
    checks: list[dict[str, Any]] = []

    def add(check: str, count: int, denominator: int, table: str = "Orders") -> None:
        checks.append(
            {
                "table": table,
                "check": check,
                "records": int(count),
                "pct": pct(count, denominator),
            }
        )

    add("Missing purchase timestamp", int(orders["purchase_ts"].isna().sum()), len(orders))
    add("Missing approval timestamp", int(orders["approved_ts"].isna().sum()), len(orders))
    add("Missing carrier timestamp", int(orders["carrier_ts"].isna().sum()), len(orders))
    add("Missing delivery timestamp", int(orders["delivered_ts"].isna().sum()), len(orders))
    add("Missing estimated delivery timestamp", int(orders["estimated_ts"].isna().sum()), len(orders))

    approved = orders[orders["approved_ts"].notna() & orders["purchase_ts"].notna()]
    add(
        "Approved before purchase",
        int(approved["approved_ts"].lt(approved["purchase_ts"]).sum()),
        len(approved),
    )
    carrier = orders[orders["carrier_ts"].notna() & orders["purchase_ts"].notna()]
    add(
        "Carrier handoff before purchase",
        int(carrier["carrier_ts"].lt(carrier["purchase_ts"]).sum()),
        len(carrier),
    )
    delivered = orders[orders["delivered_ts"].notna() & orders["purchase_ts"].notna()]
    add(
        "Delivered before purchase",
        int(delivered["delivered_ts"].lt(delivered["purchase_ts"]).sum()),
        len(delivered),
    )
    both = orders[orders["delivered_ts"].notna() & orders["carrier_ts"].notna()]
    add(
        "Delivered before carrier handoff",
        int(both["delivered_ts"].lt(both["carrier_ts"]).sum()),
        len(both),
    )
    estimated = orders[orders["estimated_ts"].notna() & orders["purchase_ts"].notna()]
    add(
        "Estimated delivery before purchase",
        int(estimated["estimated_ts"].lt(estimated["purchase_ts"]).sum()),
        len(estimated),
    )
    add(
        "Delivered status without delivery date",
        int(
            (
                orders["order_status"].eq("delivered")
                & orders["delivered_ts"].isna()
            ).sum()
        ),
        int(orders["order_status"].eq("delivered").sum()),
    )
    add(
        "Delivery time over 365 days",
        int((orders["has_delivery_dates"] & orders["delivery_days"].gt(365)).sum()),
        int(orders["has_delivery_dates"].sum()),
    )

    item_dates = items.merge(
        orders[["order_id", "purchase_ts"]], on="order_id", how="left"
    )
    item_dates = item_dates[
        item_dates["shipping_limit_date"].notna() & item_dates["purchase_ts"].notna()
    ]
    add(
        "Shipping limit before purchase",
        int(item_dates["shipping_limit_date"].lt(item_dates["purchase_ts"]).sum()),
        len(item_dates),
        table="Order items",
    )

    review_dates = reviews.merge(
        orders[["order_id", "purchase_ts"]], on="order_id", how="left"
    )
    creation_valid = review_dates[
        review_dates["review_creation_date"].notna() & review_dates["purchase_ts"].notna()
    ]
    add(
        "Review created before purchase",
        int(
            creation_valid["review_creation_date"]
            .lt(creation_valid["purchase_ts"])
            .sum()
        ),
        len(creation_valid),
        table="Reviews",
    )
    answer_valid = review_dates[
        review_dates["review_creation_date"].notna()
        & review_dates["review_answer_timestamp"].notna()
    ]
    add(
        "Review answered before creation",
        int(
            answer_valid["review_answer_timestamp"]
            .lt(answer_valid["review_creation_date"])
            .sum()
        ),
        len(answer_valid),
        table="Reviews",
    )
    return pd.DataFrame(checks, columns=["table", "check", "records", "pct"])


def _referential_integrity(data: dict[str, Any]) -> pd.DataFrame:
    orders = data["orders"]
    items = data["items"]
    payments = data["payments"]
    reviews = data["reviews_all"]
    customers = data["customers"]
    products = data["products"]
    sellers = data["sellers"]
    translation = data["translation"]
    untranslated_categories = products["product_category_name"].dropna()
    untranslated_count = int(
        (~untranslated_categories.isin(set(translation["product_category_name"]))).sum()
    )
    checks = [
        (
            "Orders → customers",
            "order.customer_id",
            "customer.customer_id",
            int((~orders["customer_id"].isin(set(customers["customer_id"]))).sum()),
            "critical",
        ),
        (
            "Order items → orders",
            "item.order_id",
            "order.order_id",
            int((~items["order_id"].isin(set(orders["order_id"]))).sum()),
            "critical",
        ),
        (
            "Order items → products",
            "item.product_id",
            "product.product_id",
            int((~items["product_id"].isin(set(products["product_id"]))).sum()),
            "critical",
        ),
        (
            "Order items → sellers",
            "item.seller_id",
            "seller.seller_id",
            int((~items["seller_id"].isin(set(sellers["seller_id"]))).sum()),
            "critical",
        ),
        (
            "Payments → orders",
            "payment.order_id",
            "order.order_id",
            int((~payments["order_id"].isin(set(orders["order_id"]))).sum()),
            "critical",
        ),
        (
            "Reviews → orders",
            "review.order_id",
            "order.order_id",
            int((~reviews["order_id"].isin(set(orders["order_id"]))).sum()),
            "critical",
        ),
        (
            "Product categories → translation",
            "product.product_category_name",
            "translation.product_category_name",
            untranslated_count,
            "warning",
        ),
    ]
    return pd.DataFrame(
        checks, columns=["relationship", "child_key", "parent_key", "orphans", "severity"]
    )


def _duplicate_keys(data: dict[str, Any]) -> pd.DataFrame:
    orders = data["orders"]
    items = data["items"]
    payments = data["payments"]
    reviews = data["reviews_all"]
    customers = data["customers"]
    products = data["products"]
    sellers = data["sellers"]
    checks = [
        ("Orders", "order_id", int(orders.duplicated(subset=["order_id"]).sum()), "critical"),
        ("Customers", "customer_id", int(customers.duplicated(subset=["customer_id"]).sum()), "critical"),
        (
            "Customers",
            "customer_unique_id",
            int(customers.duplicated(subset=["customer_unique_id"]).sum()),
            "expected",
        ),
        ("Products", "product_id", int(products.duplicated(subset=["product_id"]).sum()), "critical"),
        ("Sellers", "seller_id", int(sellers.duplicated(subset=["seller_id"]).sum()), "critical"),
        ("Reviews", "review_id", int(reviews.duplicated(subset=["review_id"]).sum()), "warning"),
        (
            "Reviews",
            "order_id (multiple reviews)",
            int(reviews.duplicated(subset=["order_id"]).sum()),
            "warning",
        ),
        (
            "Order items",
            "(order_id, order_item_id)",
            int(items.duplicated(subset=["order_id", "order_item_id"]).sum()),
            "critical",
        ),
        (
            "Payments",
            "(order_id, payment_sequential)",
            int(payments.duplicated(subset=["order_id", "payment_sequential"]).sum()),
            "critical",
        ),
    ]
    return pd.DataFrame(checks, columns=["table", "key", "duplicate_rows", "severity"])


def _coverage_checks(data: dict[str, Any]) -> pd.DataFrame:
    orders = data["orders"]
    items = data["items"]
    payments = data["payments"]
    reviews = data["reviews"]
    checks = [
        (
            "Orders without items",
            int((~orders["order_id"].isin(set(items["order_id"]))).sum()),
            len(orders),
        ),
        (
            "Orders without payments",
            int((~orders["order_id"].isin(set(payments["order_id"]))).sum()),
            len(orders),
        ),
        (
            "Orders without reviews",
            int((~orders["order_id"].isin(set(reviews["order_id"]))).sum()),
            len(orders),
        ),
        (
            "Customers without orders",
            int((~data["customers"]["customer_id"].isin(set(orders["customer_id"]))).sum()),
            len(data["customers"]),
        ),
    ]
    frame = pd.DataFrame(checks, columns=["check", "records", "denominator"])
    frame["pct"] = frame.apply(lambda row: pct(row["records"], row["denominator"]), axis=1)
    return frame


def quality_report(data: dict[str, Any]) -> dict[str, Any]:
    """Build all data quality tables used by the Data Quality page."""
    table_names = ["orders", "items", "payments", "reviews_all", "customers", "products", "sellers", "translation"]
    profiles = pd.DataFrame([_table_profile(name, data[name]) for name in table_names])
    missing = _missing_details(data)
    invalid_dates = _invalid_dates(data)
    integrity = _referential_integrity(data)
    duplicates = _duplicate_keys(data)
    coverage = _coverage_checks(data)

    serious_duplicates = duplicates[duplicates["severity"] == "critical"]["duplicate_rows"].sum()
    invalid_total = int(
        invalid_dates[
            invalid_dates["check"].isin(
                [
                    "Approved before purchase",
                    "Carrier handoff before purchase",
                    "Delivered before purchase",
                    "Delivered before carrier handoff",
                    "Estimated delivery before purchase",
                    "Delivered status without delivery date",
                    "Shipping limit before purchase",
                    "Review created before purchase",
                    "Review answered before creation",
                ]
            )
        ]["records"].sum()
    )
    summary = {
        "tables_profiled": int(len(profiles)),
        "rows_profiled": int(profiles["rows"].sum()),
        "missing_cells": int(profiles["missing_cells"].sum()),
        "duplicate_rows": int(profiles["duplicate_rows"].sum()),
        "duplicate_key_issues": int(serious_duplicates),
        "invalid_date_records": invalid_total,
        "orphan_records": int(integrity["orphans"].sum()),
        "coverage_issues": int(coverage["records"].sum()),
    }
    return {
        "profiles": profiles,
        "missing": missing,
        "invalid_dates": invalid_dates,
        "integrity": integrity,
        "duplicates": duplicates,
        "coverage": coverage,
        "summary": summary,
        "table_counts": data["metadata"]["table_counts"],
    }
