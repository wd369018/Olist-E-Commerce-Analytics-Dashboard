"""Tests for source loading and order-level data modelling."""
from __future__ import annotations

import pytest

from dashboard.config import resolve_db_path
from dashboard.data import item_aggregates, load_data, payment_aggregates


def test_database_is_resolved_and_not_empty():
    path = resolve_db_path()
    assert path.exists()
    assert path.stat().st_size > 0
    assert "olist_ecommerce.db" in path.name


def test_core_row_counts(data):
    assert data["metadata"]["order_count"] == 99_441
    assert len(data["orders"]) == 99_441
    assert len(data["items"]) == 112_650
    assert len(data["payments"]) == 103_886
    assert len(data["reviews_all"]) == 99_224
    assert len(data["reviews"]) == 98_673
    assert len(data["customers"]) == 99_441
    assert len(data["products"]) == 32_951
    assert len(data["sellers"]) == 3_095


def test_orders_are_unique(data):
    assert data["orders"]["order_id"].duplicated().sum() == 0
    assert data["reviews"]["order_id"].duplicated().sum() == 0


def test_reviews_are_deduplicated_to_latest(data):
    raw = data["reviews_all"]
    deduped = data["reviews"]
    assert len(deduped) == raw["order_id"].nunique()
    expected = (
        raw.sort_values(
            ["order_id", "review_answer_timestamp", "review_creation_date", "review_id"],
            na_position="first",
        )
        .drop_duplicates("order_id", keep="last")
        .set_index("order_id")
    )
    actual = deduped.set_index("order_id")
    assert actual.index.equals(expected.index)
    assert (actual["review_id"] == expected["review_id"]).all()


def test_sentinel_values_become_missing(data):
    orders = data["orders"]
    # The processed layer stores missing delivery dates as the text '0'.
    assert orders["delivered_ts"].isna().sum() == 2_965
    assert not (orders["order_status"] == "0").any()
    assert not (data["items"]["category"] == "0").any()
    assert data["items"]["category"].notna().all()
    # Review comments use '0' as a placeholder for "no comment".
    assert data["reviews_all"]["review_comment_message"].isna().sum() == 58_276
    assert not (data["reviews_all"]["review_comment_message"] == "0").any()


def test_delivery_flags_are_internally_consistent(data):
    orders = data["orders"]
    assert (orders["delivery_days"].dropna() >= 0).all()
    assert orders.loc[orders["has_delivery_dates"], "delivered_ts"].notna().all()
    assert orders.loc[orders["has_delivery_dates"], "estimated_ts"].notna().all()
    assert orders.loc[orders["has_delivery_dates"], "purchase_ts"].notna().all()
    assert orders["is_late"].dtype == bool
    # Canceled orders can carry a delivery timestamp; they are not late deliveries.
    canceled_with_dates = orders[(orders["order_status"] == "canceled") & orders["has_delivery_dates"]]
    assert len(canceled_with_dates) == 6


def test_item_aggregation_is_one_row_per_order(data):
    aggregates = item_aggregates(data["items"])
    assert aggregates["order_id"].is_unique
    assert len(aggregates) == data["items"]["order_id"].nunique()
    assert aggregates["item_revenue"].sum() == pytest.approx(data["items"]["price"].sum(), rel=1e-9)
    assert aggregates["gross_revenue"].sum() == pytest.approx(
        data["items"]["gross_value"].sum(), rel=1e-9
    )


def test_payment_aggregation_is_one_row_per_order(data):
    aggregates = payment_aggregates(data["payments"])
    assert aggregates["order_id"].is_unique
    assert len(aggregates) == data["payments"]["order_id"].nunique()
    assert aggregates["payment_value"].sum() == pytest.approx(
        data["payments"]["payment_value"].sum(), rel=1e-9
    )


def test_missing_database_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_data(tmp_path / "missing.db")
    empty = tmp_path / "empty.db"
    empty.write_bytes(b"")
    with pytest.raises(FileNotFoundError):
        load_data(empty)
