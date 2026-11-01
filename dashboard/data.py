"""Data access and preparation for the Olist dashboard.

SQLite and Parquet sources are read without modification. Preparation keeps
one-to-many tables separate so they cannot duplicate orders or revenue.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from .config import METRIC_HELP, SENTINEL_VALUES

DATE_COLUMNS = [
    "order_purchase_timestamp",
    "order_approved_at",
    "order_delivered_carrier_date",
    "order_delivered_customer_date",
    "order_estimated_delivery_date",
]

REVIEW_DATE_COLUMNS = ["review_creation_date", "review_answer_timestamp"]
PARQUET_TABLES = [
    "olist_customers_dataset",
    "olist_orders_dataset",
    "olist_order_items_dataset",
    "olist_order_payments_dataset",
    "olist_order_reviews_dataset",
    "olist_products_dataset",
    "olist_sellers_dataset",
    "product_category_name_translation",
]


def _read_table(conn: sqlite3.Connection, table: str) -> pd.DataFrame:
    return pd.read_sql_query(f'SELECT * FROM "{table}"', conn)


def _clean_text(series: pd.Series, sentinels: set[str] | None = None) -> pd.Series:
    """Trim text and replace known sentinel placeholders with missing values."""
    sentinels = sentinels or SENTINEL_VALUES
    cleaned = series.astype("string").str.strip()
    return cleaned.mask(cleaned.str.lower().isin(sentinels))


def _parse_dates(series: pd.Series) -> pd.Series:
    """Parse Olist timestamps, treating sentinel values such as '0' as missing."""
    cleaned = _clean_text(series)
    parsed = pd.to_datetime(cleaned, errors="coerce", format="%Y-%m-%d %H:%M:%S")
    # Fall back to pandas' mixed parser for any non-standard values.
    unresolved = parsed.isna() & cleaned.notna()
    if unresolved.any():
        parsed.loc[unresolved] = pd.to_datetime(cleaned.loc[unresolved], errors="coerce", format="mixed")
    return parsed


def _title_city(series: pd.Series) -> pd.Series:
    return series.astype("string").str.strip().str.title()


def load_data(db_path: str | Path) -> dict[str, Any]:
    """Load and model every table used by the dashboard from SQLite or Parquet.

    Returns a dictionary of DataFrames plus a ``metadata`` dictionary. SQLite
    connections are read-only, and Parquet sources are not modified.
    """
    db_path = Path(db_path)
    if not db_path.exists():
        raise FileNotFoundError(f"Olist data source not found: {db_path}")

    if db_path.is_dir():
        missing_tables = [
            table for table in PARQUET_TABLES if not (db_path / f"{table}.parquet").is_file()
        ]
        if missing_tables:
            raise FileNotFoundError(
                f"Missing required Parquet datasets in {db_path}: {', '.join(missing_tables)}"
            )
        table_frames = {
            table: pd.read_parquet(db_path / f"{table}.parquet") for table in PARQUET_TABLES
        }
        table_counts = {
            file.stem: int(pq.ParquetFile(file).metadata.num_rows)
            for file in db_path.glob("*.parquet")
        }
        source_size = sum(file.stat().st_size for file in db_path.glob("*.parquet"))
    else:
        if db_path.stat().st_size == 0:
            raise FileNotFoundError(f"Olist database not found or empty: {db_path}")
        conn = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
        try:
            table_frames = {
                table: _read_table(conn, table) for table in PARQUET_TABLES
            }
            table_counts = {}
            for (table,) in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall():
                table_counts[table] = int(
                    conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
                )
        finally:
            conn.close()
        source_size = db_path.stat().st_size

    customers = table_frames["olist_customers_dataset"]
    orders = table_frames["olist_orders_dataset"]
    items = table_frames["olist_order_items_dataset"]
    payments = table_frames["olist_order_payments_dataset"]
    reviews_all = table_frames["olist_order_reviews_dataset"]
    products = table_frames["olist_products_dataset"]
    sellers = table_frames["olist_sellers_dataset"]
    translation = table_frames["product_category_name_translation"]

    # ------------------------------------------------------------------ customers
    customers["customer_id"] = customers["customer_id"].astype("string")
    customers["customer_unique_id"] = customers["customer_unique_id"].astype("string")
    customers["customer_state"] = customers["customer_state"].astype("string").str.upper().str.strip()
    customers["customer_city"] = _title_city(customers["customer_city"])
    customers["customer_zip_code_prefix"] = pd.to_numeric(
        customers["customer_zip_code_prefix"], errors="coerce"
    ).astype("Int64")

    # --------------------------------------------------------------------- orders
    orders["order_id"] = orders["order_id"].astype("string")
    orders["customer_id"] = orders["customer_id"].astype("string")
    orders["order_status"] = orders["order_status"].astype("string").str.lower().str.strip()
    for column in DATE_COLUMNS:
        orders[column] = _parse_dates(orders[column])

    orders = orders.rename(
        columns={
            "order_purchase_timestamp": "purchase_ts",
            "order_approved_at": "approved_ts",
            "order_delivered_carrier_date": "carrier_ts",
            "order_delivered_customer_date": "delivered_ts",
            "order_estimated_delivery_date": "estimated_ts",
        }
    )
    orders = orders.merge(
        customers[
            ["customer_id", "customer_unique_id", "customer_state", "customer_city"]
        ],
        on="customer_id",
        how="left",
    )
    orders["customer_state"] = orders["customer_state"].fillna("Unknown")
    orders["customer_city"] = orders["customer_city"].fillna("Unknown")
    orders["customer_unique_id"] = orders["customer_unique_id"].fillna(orders["customer_id"])

    orders["purchase_date"] = orders["purchase_ts"].dt.normalize()
    orders["purchase_month"] = orders["purchase_ts"].dt.to_period("M").dt.to_timestamp()
    orders["purchase_weekday"] = orders["purchase_ts"].dt.day_name()
    orders["is_delivered"] = orders["order_status"].eq("delivered")
    orders["is_canceled"] = orders["order_status"].eq("canceled")
    orders["is_valid_sale"] = ~orders["order_status"].isin(["canceled", "unavailable"])

    # Durations are in fractional days. Invalid/negative values are flagged later.
    orders["delivery_days"] = (
        orders["delivered_ts"] - orders["purchase_ts"]
    ).dt.total_seconds() / 86400
    orders["estimated_days"] = (
        orders["estimated_ts"] - orders["purchase_ts"]
    ).dt.total_seconds() / 86400
    orders["delay_days"] = (
        orders["delivered_ts"] - orders["estimated_ts"]
    ).dt.total_seconds() / 86400
    orders["carrier_days"] = (
        orders["carrier_ts"] - orders["purchase_ts"]
    ).dt.total_seconds() / 86400
    orders["transit_days"] = (
        orders["delivered_ts"] - orders["carrier_ts"]
    ).dt.total_seconds() / 86400
    orders["has_delivery_dates"] = (
        orders["delivered_ts"].notna()
        & orders["estimated_ts"].notna()
        & orders["purchase_ts"].notna()
        & orders["delivery_days"].ge(0)
    )
    orders["is_late"] = False
    orders.loc[orders["has_delivery_dates"], "is_late"] = (
        orders.loc[orders["has_delivery_dates"], "delivered_ts"]
        > orders.loc[orders["has_delivery_dates"], "estimated_ts"]
    )

    # ------------------------------------------------------------------ products
    products["product_id"] = products["product_id"].astype("string")
    products["product_category_name"] = _clean_text(products["product_category_name"])
    translation["product_category_name"] = translation["product_category_name"].astype("string")
    translation["product_category_name_english"] = translation[
        "product_category_name_english"
    ].astype("string")
    products = products.merge(translation, on="product_category_name", how="left")
    category = products["product_category_name_english"].copy()
    fallback = (
        products["product_category_name"]
        .fillna("uncategorized")
        .str.replace("_", " ", regex=False)
        .str.title()
    )
    category = category.fillna(fallback)
    category = category.mask(category.str.lower().isin(SENTINEL_VALUES), "Uncategorized")
    products["category"] = category.fillna("Uncategorized")
    for column in [
        "product_name_lenght",
        "product_description_lenght",
        "product_photos_qty",
        "product_weight_g",
        "product_length_cm",
        "product_height_cm",
        "product_width_cm",
    ]:
        products[column] = pd.to_numeric(products[column], errors="coerce")

    # ------------------------------------------------------------------- sellers
    sellers["seller_id"] = sellers["seller_id"].astype("string")
    sellers["seller_state"] = sellers["seller_state"].astype("string").str.upper().str.strip()
    sellers["seller_city"] = _title_city(sellers["seller_city"])
    sellers["seller_zip_code_prefix"] = pd.to_numeric(
        sellers["seller_zip_code_prefix"], errors="coerce"
    ).astype("Int64")

    # --------------------------------------------------------------------- items
    items["order_id"] = items["order_id"].astype("string")
    items["product_id"] = items["product_id"].astype("string")
    items["seller_id"] = items["seller_id"].astype("string")
    items["shipping_limit_date"] = _parse_dates(items["shipping_limit_date"])
    items["price"] = pd.to_numeric(items["price"], errors="coerce").fillna(0.0)
    items["freight_value"] = pd.to_numeric(items["freight_value"], errors="coerce").fillna(0.0)
    items["order_item_id"] = pd.to_numeric(items["order_item_id"], errors="coerce").fillna(0).astype(int)
    items = items.merge(
        products[
            [
                "product_id",
                "product_category_name",
                "category",
                "product_photos_qty",
                "product_weight_g",
            ]
        ],
        on="product_id",
        how="left",
    )
    items = items.merge(
        sellers[["seller_id", "seller_city", "seller_state"]],
        on="seller_id",
        how="left",
    )
    items["category"] = items["category"].fillna("Uncategorized")
    items["gross_value"] = items["price"] + items["freight_value"]
    items["seller_city"] = items["seller_city"].fillna("Unknown")
    items["seller_state"] = items["seller_state"].fillna("Unknown")

    # ------------------------------------------------------------------ payments
    payments["order_id"] = payments["order_id"].astype("string")
    payments["payment_type"] = (
        payments["payment_type"].astype("string").str.lower().str.strip().fillna("not_defined")
    )
    payments["payment_installments"] = pd.to_numeric(
        payments["payment_installments"], errors="coerce"
    ).fillna(0).astype(int)
    payments["payment_value"] = pd.to_numeric(
        payments["payment_value"], errors="coerce"
    ).fillna(0.0)

    # ------------------------------------------------------------------- reviews
    reviews_all["review_id"] = reviews_all["review_id"].astype("string")
    reviews_all["order_id"] = reviews_all["order_id"].astype("string")
    reviews_all["review_score"] = pd.to_numeric(
        reviews_all["review_score"], errors="coerce"
    )
    for column in ["review_comment_title", "review_comment_message"]:
        if column in reviews_all.columns:
            reviews_all[column] = _clean_text(reviews_all[column])
    for column in REVIEW_DATE_COLUMNS:
        reviews_all[column] = _parse_dates(reviews_all[column])

    # A small number of orders have more than one review. Keep the latest review
    # per order so satisfaction metrics never double-count an order.
    reviews = (
        reviews_all.sort_values(
            ["order_id", "review_answer_timestamp", "review_creation_date", "review_id"],
            na_position="first",
        )
        .drop_duplicates("order_id", keep="last")
        .copy()
    )

    metadata = {
        "db_path": str(db_path),
        "db_size_mb": round(source_size / 1_000_000, 1),
        "table_counts": table_counts,
        "order_count": int(orders["order_id"].nunique()),
        "review_count": len(reviews),
        "date_min": orders["purchase_ts"].min(),
        "date_max": orders["purchase_ts"].max(),
        "metric_help": METRIC_HELP,
        "sentinel_note": (
            "Some source formats store missing dates, categories and review comments "
            "as the text value '0'. These are normalised to missing values."
        ),
    }

    return {
        "customers": customers,
        "orders": orders,
        "items": items,
        "payments": payments,
        "reviews_all": reviews_all,
        "reviews": reviews,
        "products": products,
        "sellers": sellers,
        "translation": translation,
        "metadata": metadata,
    }


def item_aggregates(items: pd.DataFrame) -> pd.DataFrame:
    """Aggregate item rows to exactly one row per order."""
    columns = [
        "order_id",
        "item_revenue",
        "freight_revenue",
        "gross_revenue",
        "item_count",
        "product_count",
        "seller_count",
    ]
    if items.empty:
        return pd.DataFrame(columns=columns)
    grouped = (
        items.groupby("order_id", as_index=False)
        .agg(
            item_revenue=("price", "sum"),
            freight_revenue=("freight_value", "sum"),
            gross_revenue=("gross_value", "sum"),
            item_count=("order_item_id", "size"),
            product_count=("product_id", "nunique"),
            seller_count=("seller_id", "nunique"),
        )
    )
    return grouped[columns]


def payment_aggregates(payments: pd.DataFrame) -> pd.DataFrame:
    """Aggregate payment rows to exactly one row per order."""
    columns = [
        "order_id",
        "payment_value",
        "payment_records",
        "max_installments",
        "primary_payment_type",
        "payment_type_list",
    ]
    if payments.empty:
        return pd.DataFrame(columns=columns)
    grouped = (
        payments.groupby("order_id", as_index=False)
        .agg(
            payment_value=("payment_value", "sum"),
            payment_records=("payment_sequential", "size"),
            max_installments=("payment_installments", "max"),
        )
    )
    primary = (
        payments.sort_values(["order_id", "payment_sequential"])
        .drop_duplicates("order_id", keep="first")[["order_id", "payment_type"]]
        .rename(columns={"payment_type": "primary_payment_type"})
    )
    type_lists = (
        payments.groupby("order_id")["payment_type"]
        .apply(lambda values: ", ".join(sorted(set(values.astype(str)))))
        .reset_index(name="payment_type_list")
    )
    grouped = grouped.merge(primary, on="order_id", how="left").merge(type_lists, on="order_id", how="left")
    return grouped[columns]


def data_profile(data: dict[str, Any]) -> dict[str, Any]:
    """Basic source metadata used by the sidebar and data quality page."""
    orders = data["orders"]
    return {
        "min_date": orders["purchase_ts"].min(),
        "max_date": orders["purchase_ts"].max(),
        "statuses": sorted(orders["order_status"].dropna().unique().tolist()),
        "states": sorted(data["customers"]["customer_state"].dropna().unique().tolist()),
        "categories": sorted(data["items"]["category"].dropna().unique().tolist()),
    }


def make_empty_orders() -> pd.DataFrame:
    """Column-complete empty order frame used as a safe fallback."""
    return pd.DataFrame(
        columns=[
            "order_id",
            "customer_id",
            "order_status",
            "purchase_ts",
            "approved_ts",
            "carrier_ts",
            "delivered_ts",
            "estimated_ts",
            "customer_unique_id",
            "customer_state",
            "customer_city",
            "purchase_date",
            "purchase_month",
            "purchase_weekday",
            "is_delivered",
            "is_canceled",
            "is_valid_sale",
            "delivery_days",
            "estimated_days",
            "delay_days",
            "carrier_days",
            "transit_days",
            "has_delivery_dates",
            "is_late",
            "item_revenue",
            "freight_revenue",
            "gross_revenue",
            "item_count",
            "product_count",
            "seller_count",
            "payment_value",
            "payment_records",
            "max_installments",
            "primary_payment_type",
            "payment_type_list",
            "review_score",
            "review_creation_date",
            "review_answer_timestamp",
        ]
    )
