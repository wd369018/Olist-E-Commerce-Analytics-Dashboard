"""Shared fixtures for the Olist dashboard test suite."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest

from dashboard.config import resolve_db_path
from dashboard.data import load_data
from dashboard.filters import FilterSelection, apply_filters


@pytest.fixture(scope="session")
def data():
    return load_data(resolve_db_path())


@pytest.fixture(scope="session")
def ctx(data):
    return apply_filters(data, FilterSelection())


@pytest.fixture(scope="session")
def empty_ctx(data):
    from datetime import date

    return apply_filters(
        data,
        FilterSelection(start_date=date(2016, 1, 1), end_date=date(2016, 1, 31)),
    )
