"""Tests for filter application and join fan-out protection."""
from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from dashboard.filters import FilterSelection, apply_filters


def test_default_filter_keeps_every_order(ctx):
    assert len(ctx.orders) == 99_441
    assert ctx.orders["order_id"].is_unique
    assert len(ctx.payments) == 103_886
    assert len(ctx.reviews) == 98_673
    assert ctx.total_orders_unfiltered == 99_441


def test_order_level_frames_have_one_row_per_order(ctx):
    assert ctx.orders["order_id"].is_unique
    assert len(ctx.orders) == ctx.orders["order_id"].nunique()
    # Order-level item values cover every item row in scope, including canceled
    # orders. Revenue KPIs use ctx.valid_items, which excludes them.
    assert ctx.orders["item_revenue"].sum() == pytest.approx(ctx.items["price"].sum(), rel=1e-9)
    assert ctx.orders["payment_value"].sum() == pytest.approx(
        ctx.payments["payment_value"].sum(), rel=1e-9
    )


def test_status_filter_excludes_revenue_for_canceled_orders(data):
    canceled = apply_filters(data, FilterSelection(statuses=("canceled",)))
    assert len(canceled.orders) == 625
    assert canceled.orders["is_canceled"].all()
    assert canceled.valid_items.empty
    assert canceled.orders["item_revenue"].sum() == pytest.approx(
        canceled.items["price"].sum(), rel=1e-9
    )


def test_category_filter_scopes_items_and_orders(data):
    category = "health_beauty"
    filtered = apply_filters(data, FilterSelection(categories=(category,)))
    assert not filtered.items.empty
    assert (filtered.items["category"] == category).all()
    assert set(filtered.items["order_id"]).issubset(set(filtered.orders["order_id"]))
    # Orders are restricted to those containing the selected category.
    assert filtered.orders["item_count"].gt(0).all()
    assert filtered.orders["item_revenue"].sum() == pytest.approx(
        filtered.items["price"].sum(), rel=1e-9
    )
    assert len(filtered.orders) == filtered.items["order_id"].nunique()
    assert any("Category filter" in note for note in filtered.notes)


def test_date_filter_is_inclusive(data):
    start, end = date(2018, 1, 1), date(2018, 1, 31)
    filtered = apply_filters(data, FilterSelection(start_date=start, end_date=end))
    assert not filtered.orders.empty
    days = pd.to_datetime(filtered.orders["purchase_date"]).dt.date
    assert days.min() >= start
    assert days.max() <= end


def test_state_filter(data):
    filtered = apply_filters(data, FilterSelection(states=("SP", "RJ")))
    assert not filtered.orders.empty
    assert set(filtered.orders["customer_state"]) <= {"SP", "RJ"}


def test_no_matching_orders_returns_empty_context(empty_ctx):
    assert empty_ctx.orders.empty
    assert empty_ctx.items.empty
    assert empty_ctx.payments.empty
    assert empty_ctx.reviews.empty


def test_invalid_date_range_raises(data):
    with pytest.raises(ValueError):
        apply_filters(
            data,
            FilterSelection(start_date=date(2018, 2, 1), end_date=date(2018, 1, 1)),
        )


def test_stale_filter_values_are_harmless(data):
    # Unknown option values simply match nothing instead of raising.
    filtered = apply_filters(data, FilterSelection(states=("ZZ",)))
    assert filtered.orders.empty
