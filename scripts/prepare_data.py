"""Prepare CSV source datasets as Parquet for deployment."""
from __future__ import annotations

import argparse
from pathlib import Path

from dashboard.data import PARQUET_TABLES
from utils.data_loader import convert_csv_to_parquet


def prepare_data(
    csv_dir: Path | str | None = None,
    output_dir: Path | str | None = None,
    force: bool = False,
) -> dict[str, Path]:
    """Convert CSV datasets and verify all tables required by the dashboard."""
    converted = convert_csv_to_parquet(csv_dir, output_dir, force=force)
    missing = [
        table
        for table in PARQUET_TABLES
        if table not in converted or not converted[table].is_file()
    ]
    if missing:
        raise FileNotFoundError(
            "Could not prepare a complete dashboard dataset. Missing tables: "
            f"{', '.join(missing)}. Provide the source CSV files or an existing "
            "Parquet dataset."
        )
    return {table: converted[table] for table in PARQUET_TABLES}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Convert Olist CSV files to the Parquet format used by the dashboard."
    )
    parser.add_argument(
        "--csv-dir",
        type=Path,
        help="Directory containing the source CSV files (or set OLIST_CSV_DIR).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Output directory (or set OLIST_PARQUET_DIR).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rebuild Parquet files even when they are already up to date.",
    )
    args = parser.parse_args(argv)

    datasets = prepare_data(args.csv_dir, args.output_dir, force=args.force)
    output_dir = next(iter(datasets.values())).parent
    print(f"Prepared {len(datasets)} dashboard datasets in {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
