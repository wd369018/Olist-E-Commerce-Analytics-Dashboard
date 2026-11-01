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
from dashboard.data import PARQUET_TABLES, load_data

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


def _configured_path(variable: str, default: Path) -> Path:
    """Return a configured data path, expanding a user-home prefix if present."""
    value = os.getenv(variable)
    return Path(value).expanduser() if value and value.strip() else default


def convert_csv_to_parquet(
    csv_dir: Path | str | None = None,
    target_dir: Path | str | None = None,
    engine: str = "pyarrow",
    force: bool = False,
) -> dict[str, Path]:
    """Convert raw CSV files to compressed .parquet format using pyarrow.

    Returns a mapping of table name to the generated parquet file path.
    """
    csv_dir = (
        Path(csv_dir)
        if csv_dir is not None
        else _configured_path("OLIST_CSV_DIR", PROJECT_ROOT)
    )
    target_dir = (
        Path(target_dir)
        if target_dir is not None
        else _configured_path("OLIST_PARQUET_DIR", PARQUET_DIR)
    )
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
    """Resolve the configured source without writing when Parquet is already complete."""
    if os.getenv("OLIST_DB_PATH"):
        return resolve_db_path()

    parquet_dir = _configured_path("OLIST_PARQUET_DIR", PARQUET_DIR)

    def missing_tables() -> list[str]:
        return [
            table
            for table in PARQUET_TABLES
            if not (parquet_dir / f"{table}.parquet").is_file()
        ]

    missing = missing_tables()
    if not missing:
        return parquet_dir

    parquet_files = convert_csv_to_parquet(target_dir=parquet_dir)
    missing = [
        table
        for table in PARQUET_TABLES
        if table not in parquet_files or not parquet_files[table].is_file()
    ]
    if not missing:
        return parquet_dir

    if os.getenv("OLIST_PARQUET_DIR"):
        raise FileNotFoundError(
            f"Incomplete Parquet dataset in {parquet_dir}. Missing required tables: "
            f"{', '.join(missing)}. Set OLIST_CSV_DIR to a directory containing the "
            "source CSV files, or point OLIST_PARQUET_DIR at a complete dataset."
        )

    return resolve_db_path()


def data_source_fingerprint(source_path: str | Path) -> tuple[tuple[str, int, int], ...]:
    """Return file metadata used to invalidate cached data when its source changes."""
    path = Path(source_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Olist data source not found: {path}")

    files = sorted(path.glob("*.parquet")) if path.is_dir() else [path]
    return tuple(
        (str(file), file.stat().st_size, file.stat().st_mtime_ns)
        for file in files
    )


@st.cache_data(show_spinner="Loading Olist analytics dataset…", max_entries=2)
def _load_dataset(
    source_path: str,
    source_fingerprint: tuple[tuple[str, int, int], ...],
) -> dict[str, Any]:
    _ = source_fingerprint  # Streamlit hashes this argument as part of the cache key.
    return load_data(Path(source_path))


def load_dataset(source_path: str | Path | None = None) -> dict[str, Any]:
    """Load and prepare all tables with Streamlit caching.

    Loads a Parquet directory or SQLite database and caches the resulting
    in-memory structure across page reruns. File metadata is part of the cache
    key so replacing a source at the same path cannot return stale data.
    """
    path = (
        Path(source_path).expanduser().resolve()
        if source_path is not None
        else resolve_dataset_path().resolve()
    )
    return _load_dataset(str(path), data_source_fingerprint(path))


def get_dataset(source_path: str | Path | None = None) -> dict[str, Any]:
    """Return the cached dataset for dashboard analytics."""
    return load_dataset(source_path)
