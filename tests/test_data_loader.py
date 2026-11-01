"""Tests for CSV conversion to the Parquet loading format."""
from __future__ import annotations

import pandas as pd

from utils.data_loader import CSV_TABLES, convert_csv_to_parquet


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
