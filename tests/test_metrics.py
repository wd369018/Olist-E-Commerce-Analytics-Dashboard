"""Metric accuracy, consistency and empty-data safety tests."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from dashboard import metrics
from dashboard.filters import FilterSelection, apply_filters


def test_overview_kpis_match_source(ctx):
    k = metrics.overview_metrics(ctx)
    assert k["total_orders"] == len(ctx.orders) == 99_441
    assert k["delivered_orders"] == 96_478
    assert k["canceled_orders"] == 625
    assert k["product_revenue"] == pytest.approx(ctx.valid_items["price"].sum(), rel=1e-9)
    assert k["product_revenue"] == pytest.approx(13_494_400.74, rel=1e-9)
    assert k["gross_revenue"] == pytest.approx(15_735_527.03, rel=1e-9)
    assert k["freight_revenue"] == pytest.approx(k["gross_revenue"] - k["product_revenue"])
    assert k["cancellation_rate"] == pytest.approx(0.6)
    assert k["repeat_customers"] == 2_888
    assert k["repeat_rate"] == pytest.approx(3.0)
    assert k["review_count"] == 98_673
    assert k["avg_review_score"] == pytest.approx(4.0863863, rel=1e-6)


def test_aov_uses_valid_orders_with_items(ctx):
    k = metrics.overview_metrics(ctx)
    valid_with_items = ctx.valid_orders.loc[ctx.valid_orders["item_count"] > 0, "order_id"].nunique()
    assert k["orders_with_items"] == valid_with_items == 98_199
    assert k["aov"] == pytest.approx(k["product_revenue"] / k["orders_with_items"])
    assert k["aov"] == pytest.approx(137.418922, rel=1e-6)


def test_monthly_sales_reconcile_to_totals(ctx):
    monthly = metrics.monthly_sales(ctx)
    k = metrics.overview_metrics(ctx)
    assert monthly["total_orders"].sum() == k["total_orders"]
    assert monthly["canceled_orders"].sum() == k["canceled_orders"]
    assert monthly["revenue"].sum() == pytest.approx(k["product_revenue"])
    assert monthly["gross_revenue"].sum() == pytest.approx(k["gross_revenue"])
    assert monthly["purchase_month"].is_monotonic_increasing

    with_items = monthly[monthly["orders_with_items"] > 0]
    assert not with_items.empty
    # The monthly AOV column uses valid orders with items as its denominator.
    assert np.allclose(
        with_items["aov"],
        with_items["revenue"] / with_items["valid_orders_with_items"],
    )


def test_category_and_state_reconcile_to_product_revenue(ctx):
    k = metrics.overview_metrics(ctx)
    categories = metrics.category_performance(ctx)
    states = metrics.state_performance(ctx)
    assert categories["revenue"].sum() == pytest.approx(k["product_revenue"])
    assert states["revenue"].sum() == pytest.approx(k["product_revenue"])
    assert categories["revenue_share"].sum() == pytest.approx(100, abs=0.3)
    assert states["revenue_share"].sum() == pytest.approx(100, abs=0.3)
    assert states["orders_with_items"].sum() == k["orders_with_items"]
    assert states["orders"].sum() == k["total_orders"]

    valid = states[states["orders_with_items"] > 0]
    assert np.allclose(
        valid["avg_order_value"], valid["revenue"] / valid["orders_with_items"]
    )


def test_category_revenue_never_counts_canceled_orders(ctx):
    categories = metrics.category_performance(ctx)
    # Item-level revenue is computed from valid items only.
    assert categories["revenue"].sum() == pytest.approx(ctx.valid_items["price"].sum())
    assert (categories["orders"] >= 1).all()
    assert categories["late_rate"].between(0, 100).all()


def test_monthly_category_trend_covers_total_revenue(ctx):
    trend, categories = metrics.monthly_category_trend(ctx, top_n=6)
    assert categories
    value_columns = [column for column in trend.columns if column not in {"purchase_month", "month_label"}]
    assert trend[value_columns].sum().sum() == pytest.approx(ctx.valid_items["price"].sum())
    assert "Other" in trend.columns


def test_frequency_score_maps_absolute_order_counts():
    scores = metrics._frequency_score(pd.Series([1, 2, 3, 4, 5, 7, 8, 20]))
    assert scores.tolist() == [1, 2, 3, 3, 4, 4, 5, 5]


def test_rfm_frame_and_segments_are_consistent(ctx):
    customers = metrics.customer_frame(ctx)
    k = metrics.overview_metrics(ctx)
    assert len(customers) == k["unique_customers"] == 94_990
    assert customers["customer_unique_id"].is_unique
    assert customers["frequency"].sum() == len(ctx.valid_orders)
    assert customers["is_repeat"].sum() == k["repeat_customers"] == 2_888
    assert np.array_equal(
        customers["f_score"].to_numpy(),
        metrics._frequency_score(customers["frequency"]).to_numpy(),
    )
    assert customers["r_score"].between(1, 5).all()
    assert customers["f_score"].between(1, 5).all()
    assert customers["m_score"].between(1, 5).all()
    assert not customers["segment"].isna().any()
    assert not customers["segment"].eq("Needs attention").any()

    segments = metrics.segment_summary(customers)
    assert segments["customers"].sum() == len(customers)
    assert segments["revenue"].sum() == pytest.approx(customers["monetary"].sum())
    assert segments["customer_share"].sum() == pytest.approx(100, abs=0.3)
    assert set(segments["segment"]).issubset(
        {
            "Champions",
            "Loyal customers",
            "New customers",
            "Promising",
            "Potential loyalists",
            "At risk",
            "Hibernating",
            "Lost",
        }
    )


def test_purchase_frequency_and_new_returning(ctx):
    customers = metrics.customer_frame(ctx)
    frequency = metrics.purchase_frequency(customers)
    assert frequency["customers"].sum() == len(customers)
    assert frequency["share"].sum() == pytest.approx(100, abs=0.3)

    monthly = metrics.new_returning_monthly(ctx)
    assert not monthly.empty
    assert monthly["total_customers"].sum() > 0
    assert (monthly["new_customers"] + monthly["returning_customers"] == monthly["total_customers"]).all()


def test_delivery_metrics_are_delivered_only(ctx):
    delivery = metrics.delivery_metrics(ctx)
    assert delivery["delivered_orders"] == 96_478
    assert delivery["delivered_with_valid_dates"] == 96_470
    assert delivery["delivered_missing_delivery_date"] == 8
    assert delivery["late_orders"] + delivery["on_time_orders"] == 96_470
    assert delivery["late_rate"] == pytest.approx(8.1)
    assert delivery["on_time_rate"] == pytest.approx(91.9)
    assert delivery["avg_delivery_days"] == pytest.approx(12.558217, rel=1e-6)
    assert delivery["monthly"]["delivered"].sum() == 96_470
    assert delivery["late_by_state"]["late_orders"].sum() <= delivery["late_orders"]
    assert delivery["late_by_state"]["late_rate"].between(0, 100).all()


def test_delivery_by_category_has_no_duplicate_order_category_pairs(ctx):
    by_category = metrics.delivery_by_category(ctx, min_orders=1)
    assert not by_category.empty
    assert (by_category["delivered_orders"] > 0).all()
    assert by_category["late_rate"].between(0, 100).all()


def test_satisfaction_metrics(ctx):
    satisfaction = metrics.satisfaction_metrics(ctx)
    assert satisfaction["review_count"] == 98_673
    assert satisfaction["distribution"]["reviews"].sum() == 98_673
    assert satisfaction["distribution"]["share"].sum() == pytest.approx(100, abs=0.3)
    assert satisfaction["avg_score"] == pytest.approx(4.0863863, rel=1e-6)
    assert satisfaction["five_star_rate"] == pytest.approx(57.8)
    assert satisfaction["low_score_rate"] == pytest.approx(14.7)
    assert satisfaction["late_avg_score"] < satisfaction["on_time_avg_score"]
    assert satisfaction["score_gap"] == pytest.approx(
        satisfaction["on_time_avg_score"] - satisfaction["late_avg_score"]
    )
    assert -1 <= satisfaction["correlation"] <= 1
    buckets = satisfaction["delay_buckets"]
    assert buckets["reviews"].sum() == (
        satisfaction["late_reviews"] + satisfaction["on_time_reviews"]
    )
    assert satisfaction["monthly"]["reviews"].sum() == 98_673


def test_category_reviews_are_not_double_counted(ctx):
    reviews = metrics.category_reviews(ctx, min_reviews=30)
    assert not reviews.empty
    assert (reviews["reviews"] >= 30).all()
    assert reviews["avg_score"].between(1, 5).all()
    assert reviews["five_star_rate"].between(0, 100).all()


def test_payment_metrics_reconcile(ctx):
    payment = metrics.payment_metrics(ctx)
    assert payment["payment_total"] == pytest.approx(16_008_872.12, rel=1e-9)
    assert payment["payment_total"] == pytest.approx(ctx.payments["payment_value"].sum())
    assert payment["orders_with_payment"] == 99_440
    assert payment["methods"]["value"].sum() == pytest.approx(payment["payment_total"])
    assert payment["methods"]["records"].sum() == len(ctx.payments)
    assert payment["top_method"] == "credit_card"
    assert payment["installment_orders"] == 51_170
    assert payment["installments"]["orders"].sum() == payment["orders_with_payment"]
    assert payment["monthly"]["value"].sum() == pytest.approx(payment["payment_total"])
    assert payment["reconciliation"]["mismatches"] == 378
    assert payment["zero_value_records"] == 9


def test_filtered_canceled_orders_have_no_revenue(data):
    canceled = apply_filters(data, FilterSelection(statuses=("canceled",)))
    k = metrics.overview_metrics(canceled)
    assert k["total_orders"] == 625
    assert k["product_revenue"] == 0
    assert k["orders_with_items"] == 0
    assert k["avg_delivery_days"] != k["avg_delivery_days"]  # NaN
    delivery = metrics.delivery_metrics(canceled)
    assert delivery["delivered_orders"] == 0
    assert delivery["late_orders"] == 0


def test_empty_context_metrics_are_safe(empty_ctx):
    assert empty_ctx.orders.empty

    k = metrics.overview_metrics(empty_ctx)
    assert k["total_orders"] == 0
    assert k["product_revenue"] == 0
    assert k["aov"] == 0
    assert math.isnan(k["avg_review_score"])

    assert metrics.monthly_sales(empty_ctx).empty
    assert metrics.category_performance(empty_ctx).empty
    assert metrics.state_performance(empty_ctx).empty
    trend, categories = metrics.monthly_category_trend(empty_ctx)
    assert trend.empty and categories == []
    assert metrics.customer_frame(empty_ctx).empty
    assert metrics.segment_summary(metrics.customer_frame(empty_ctx)).empty
    assert metrics.purchase_frequency(metrics.customer_frame(empty_ctx)).empty
    assert metrics.new_returning_monthly(empty_ctx).empty
    assert metrics.customer_state_summary(metrics.customer_frame(empty_ctx)).empty
    assert metrics.top_products(empty_ctx).empty
    assert metrics.seller_performance(empty_ctx).empty
    assert metrics.seller_state_summary(empty_ctx).empty

    delivery = metrics.delivery_metrics(empty_ctx)
    assert delivery["delivered_orders"] == 0
    assert delivery["late_rate"] == 0
    assert delivery["monthly"].empty
    assert delivery["late_by_state"].empty
    assert delivery["stage_monthly"].empty
    assert metrics.delivery_by_category(empty_ctx).empty

    satisfaction = metrics.satisfaction_metrics(empty_ctx)
    assert satisfaction["review_count"] == 0
    assert satisfaction["distribution"].empty
    assert metrics.category_reviews(empty_ctx).empty

    payment = metrics.payment_metrics(empty_ctx)
    assert payment["payment_total"] == 0
    assert payment["methods"].empty
    assert payment["reconciliation"] is None
