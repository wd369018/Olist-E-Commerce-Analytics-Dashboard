"""Modular high-performance data loader with Parquet and Streamlit caching.

Converts large CSV datasets to .parquet format using pyarrow for faster load times,
and caches preprocessed frames in memory with @st.cache_data.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from dashboard.config import resolve_db_path
from dashboard.data import load_data

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PARQUET_DIR = PROJECT_ROOT / "data" / "parquet"
CSV_TABLES = [
    "olist_customers_dataset",
    "olist_orders_dataset",
    "olist_order_items_dataset",
    "olist_order_payments_dataset",
    "olist_order_reviews_dataset",
    "olist_geolocation_dataset",
    "olist_products_dataset",
    "olist_sellers_dataset",
    "product_category_name_translation",
]


def convert_csv_to_parquet(
    csv_dir: Path | str | None = None,
    target_dir: Path | str | None = None,
    engine: str = "pyarrow",
    force: bool = False,
) -> dict[str, Path]:
    """Convert raw CSV files to compressed .parquet format using pyarrow.

    Returns a mapping of table name to the generated parquet file path.
    """
    csv_dir = Path(csv_dir or PROJECT_ROOT)
    target_dir = Path(target_dir or PARQUET_DIR)
    target_dir.mkdir(parents=True, exist_ok=True)

    generated: dict[str, Path] = {}
    for table in CSV_TABLES:
        csv_file = csv_dir / f"{table}.csv"
        parquet_file = target_dir / f"{table}.parquet"
        processed_csv = csv_dir / "processed" / f"{table}.csv"
        if processed_csv.exists():
            csv_file = processed_csv

        if csv_file.exists() and (
            force
            or not parquet_file.exists()
            or csv_file.stat().st_mtime > parquet_file.stat().st_mtime
        ):
            df = pd.read_csv(csv_file, low_memory=False)
            df.to_parquet(parquet_file, engine=engine, index=False)
        if parquet_file.exists():
            generated[table] = parquet_file

    return generated


def resolve_dataset_path() -> Path:
    """Prefer a complete Parquet dataset while respecting an explicit DB override."""
    if os.getenv("OLIST_DB_PATH"):
        return resolve_db_path()

    parquet_files = convert_csv_to_parquet()
    if all(table in parquet_files for table in CSV_TABLES):
        return PARQUET_DIR
    return resolve_db_path()


@st.cache_data(show_spinner="Loading Olist analytics dataset…", max_entries=2)
def load_dataset(source_path: str | Path | None = None) -> dict[str, Any]:
    """Load and prepare all tables with Streamlit caching.

    Loads a Parquet directory or SQLite database and caches the resulting
    in-memory structure across all page reruns.
    """
    path = Path(source_path) if source_path is not None else resolve_dataset_path()
    return load_data(path)


def get_dataset(source_path: str | Path | None = None) -> dict[str, Any]:
    """Return the cached dataset for dashboard analytics."""
    return load_dataset(source_path)
