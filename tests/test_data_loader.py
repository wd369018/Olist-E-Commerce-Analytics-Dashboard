"""Tests for CSV conversion to the Parquet loading format."""
from __future__ import annotations

import pandas as pd
import pytest

from scripts.prepare_data import prepare_data
from utils.data_loader import CSV_TABLES, convert_csv_to_parquet, resolve_dataset_path


def test_convert_csv_to_parquet_includes_each_olist_dataset(tmp_path):
    csv_dir = tmp_path / "csv"
    parquet_dir = tmp_path / "parquet"
    csv_dir.mkdir()
    expected = {"record_id": [1, 2], "value": ["first", "second"]}

    for table in CSV_TABLES:
        pd.DataFrame(expected).to_csv(csv_dir / f"{table}.csv", index=False)

    converted = convert_csv_to_parquet(csv_dir, parquet_dir)

    assert set(converted) == set(CSV_TABLES)
    for table, parquet_file in converted.items():
        pd.testing.assert_frame_equal(pd.read_parquet(parquet_file), pd.DataFrame(expected))


def test_convert_prefers_processed_csv_when_available(tmp_path):
    csv_dir = tmp_path / "csv"
    processed_dir = csv_dir / "processed"
    parquet_dir = tmp_path / "parquet"
    processed_dir.mkdir(parents=True)
    pd.DataFrame({"value": ["raw"]}).to_csv(
        csv_dir / f"{CSV_TABLES[0]}.csv", index=False
    )
    pd.DataFrame({"value": ["processed"]}).to_csv(
        processed_dir / f"{CSV_TABLES[0]}.csv", index=False
    )

    converted = convert_csv_to_parquet(csv_dir, parquet_dir)

    assert pd.read_parquet(converted[CSV_TABLES[0]])["value"].tolist() == ["processed"]


def test_resolve_complete_configured_parquet_without_converting(tmp_path, monkeypatch):
    parquet_dir = tmp_path / "parquet"
    parquet_dir.mkdir()
    required_tables = (
        "olist_customers_dataset",
        "olist_orders_dataset",
        "olist_order_items_dataset",
        "olist_order_payments_dataset",
        "olist_order_reviews_dataset",
        "olist_products_dataset",
        "olist_sellers_dataset",
        "product_category_name_translation",
    )
    for table in required_tables:
        (parquet_dir / f"{table}.parquet").touch()

    monkeypatch.delenv("OLIST_DB_PATH", raising=False)
    monkeypatch.setenv("OLIST_PARQUET_DIR", str(parquet_dir))

    def unexpected_conversion(*args, **kwargs):
        raise AssertionError("A complete Parquet dataset should not be rewritten.")

    monkeypatch.setattr("utils.data_loader.convert_csv_to_parquet", unexpected_conversion)

    assert resolve_dataset_path() == parquet_dir


def test_blank_path_environment_variables_use_defaults(monkeypatch):
    from utils.data_loader import PARQUET_DIR, _configured_path

    monkeypatch.setenv("OLIST_PARQUET_DIR", "")
    monkeypatch.setenv("OLIST_CSV_DIR", "   ")

    assert _configured_path("OLIST_PARQUET_DIR", PARQUET_DIR) == PARQUET_DIR
    assert _configured_path("OLIST_CSV_DIR", PARQUET_DIR) == PARQUET_DIR


def test_resolve_incomplete_configured_parquet_reports_missing_data(tmp_path, monkeypatch):
    monkeypatch.delenv("OLIST_DB_PATH", raising=False)
    monkeypatch.setenv("OLIST_PARQUET_DIR", str(tmp_path / "missing-parquet"))
    monkeypatch.setenv("OLIST_CSV_DIR", str(tmp_path / "missing-csv"))

    with pytest.raises(FileNotFoundError, match="Incomplete Parquet dataset"):
        resolve_dataset_path()


def test_prepare_data_requires_all_dashboard_tables(tmp_path):
    csv_dir = tmp_path / "csv"
    csv_dir.mkdir()
    parquet_dir = tmp_path / "parquet"
    pd.DataFrame({"value": [1]}).to_csv(
        csv_dir / f"{CSV_TABLES[0]}.csv", index=False
    )

    with pytest.raises(FileNotFoundError, match="Could not prepare a complete"):
        prepare_data(csv_dir, parquet_dir)
