"""Executive Overview page."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from .. import charts, metrics, ui
from ..config import COLORS, METRIC_HELP, STATUS_LABELS
from ..filters import AnalysisContext
from ..formatting import format_currency, format_days, format_int, format_number, format_pct


def _readout(ctx: AnalysisContext, k: dict, monthly: pd.DataFrame, categories: pd.DataFrame, states: pd.DataFrame) -> str:
    parts = []
    if not monthly.empty:
        peak = monthly.loc[monthly["revenue"].idxmax()]
        parts.append(
            f"Revenue peaked in {peak['month_label']} at {format_currency(peak['revenue'], compact=True)} "
            f"on {format_int(peak['total_orders'])} orders."
        )
    if not categories.empty:
        top = categories.iloc[0]
        parts.append(
            f"{top['category'].replace('_', ' ').title()} is the leading category with "
            f"{format_currency(top['revenue'], compact=True)} ({format_pct(top['revenue_share'])} of product revenue)."
        )
    if not states.empty:
        top_state = states.iloc[0]
        parts.append(
            f"{top_state['state_name']} accounts for {format_pct(top_state['revenue_share'])} of revenue."
        )
    if k["unique_customers"]:
        parts.append(
            f"{format_pct(k['repeat_rate'])} of customers have purchased more than once; "
            f"the average customer value is {format_currency(k['avg_customer_value'])}."
        )
    if k["delivered_orders"]:
        parts.append(
            f"{format_pct(k['late_rate'])} of delivered orders arrived after the estimated date "
            f"(average delivery {format_days(k['avg_delivery_days'])})."
        )
    return " ".join(parts)


def render(ctx: AnalysisContext) -> None:
    k = metrics.overview_metrics(ctx)
    monthly = metrics.monthly_sales(ctx)
    categories = metrics.category_performance(ctx)
    states = metrics.state_performance(ctx)

    ui.hero(
        "Executive overview",
        "Marketplace performance at a glance",
        "Track revenue, orders, fulfillment and customer loyalty across the Olist marketplace. "
        "Every number responds to the filters in the sidebar.",
        chips=[
            f"{format_int(k['total_orders'])} orders",
            f"{format_currency(k['product_revenue'], compact=True)} product revenue",
            f"{format_int(k['unique_customers'])} customers",
        ],
    )
    ui.active_filter_bar(ctx)

    cards = [
        {
            "label": "Total orders",
            "value": format_int(k["total_orders"]),
            "sub": f"{format_int(k['delivered_orders'])} delivered",
            "accent": COLORS["teal"],
            "help": METRIC_HELP["total_orders"],
        },
        {
            "label": "Delivered orders",
            "value": format_int(k["delivered_orders"]),
            "sub": f"{format_pct(k['delivery_rate'])} delivery rate",
            "accent": COLORS["green"],
            "help": METRIC_HELP["delivered_orders"],
        },
        {
            "label": "Product revenue",
            "value": format_currency(k["product_revenue"], compact=True),
            "sub": f"Gross incl. freight {format_currency(k['gross_revenue'], compact=True)}",
            "accent": COLORS["blue"],
            "help": METRIC_HELP["product_revenue"],
        },
        {
            "label": "Average order value",
            "value": format_currency(k["aov"]),
            "sub": f"{format_int(k['orders_with_items'])} orders with items",
            "accent": COLORS["violet"],
            "help": METRIC_HELP["aov"],
        },
        {
            "label": "Cancellation rate",
            "value": format_pct(k["cancellation_rate"]),
            "sub": f"{format_int(k['canceled_orders'])} canceled orders",
            "accent": COLORS["red"],
            "delta": "Lower is better",
            "delta_tone": "neutral",
            "help": METRIC_HELP["cancellation_rate"],
        },
        {
            "label": "Repeat customer rate",
            "value": format_pct(k["repeat_rate"]),
            "sub": f"{format_int(k['repeat_customers'])} of {format_int(k['unique_customers'])} customers",
            "accent": COLORS["amber"],
            "help": METRIC_HELP["repeat_rate"],
        },
    ]
    ui.kpi_cards(cards)

    secondary = [
        {
            "label": "Unique customers",
            "value": format_int(k["unique_customers"]),
            "sub": f"{format_number(k['avg_orders_per_customer'], 2)} orders per customer",
            "accent": COLORS["teal_light"],
        },
        {
            "label": "Average review score",
            "value": f"{format_number(k['avg_review_score'], 2)} / 5",
            "sub": f"{format_int(k['review_count'])} reviewed orders",
            "accent": COLORS["amber"],
            "help": METRIC_HELP["review_score"],
        },
        {
            "label": "Late delivery rate",
            "value": format_pct(k["late_rate"]),
            "sub": "Delivered after the estimate",
            "accent": COLORS["red"],
            "help": METRIC_HELP["late_rate"],
        },
        {
            "label": "Average delivery time",
            "value": format_days(k["avg_delivery_days"]),
            "sub": "Purchase to customer delivery",
            "accent": COLORS["slate"],
            "help": METRIC_HELP["delivery_days"],
        },
    ]
    ui.kpi_cards(secondary)

    if ctx.orders.empty:
        ui.empty_state()
        ui.footer_note(ctx.source_path)
        return

    if not monthly.empty:
        ui.section(
            "Revenue and order momentum",
            "Monthly product revenue and order volume. The final months of the source data are partial.",
        )
        ui.plot(charts.revenue_orders_trend(monthly), height=370)

    left, right = st.columns([1, 1.35], gap="large")
    with left:
        ui.section("Order status mix", "Share of orders by current status.")
        status_counts = (
            ctx.orders.groupby("order_status", as_index=False)["order_id"]
            .nunique()
            .sort_values("order_id", ascending=False)
        )
        status_counts["label"] = status_counts["order_status"].map(
            lambda value: STATUS_LABELS.get(value, str(value).title())
        )
        ui.plot(
            charts.donut(
                status_counts["label"],
                status_counts["order_id"],
                center_text=format_int(k["total_orders"]),
                height=360,
            ),
            height=360,
        )
    with right:
        ui.section("Top categories", "Product revenue by translated category.")
        if categories.empty:
            ui.empty_state("No category revenue", "No item revenue exists for the current selection.")
        else:
            top_categories = categories.head(12).copy()
            top_categories["display"] = top_categories["category"].str.replace("_", " ").str.title()
            ui.plot(
                charts.horizontal_bar(
                    top_categories,
                    "display",
                    "revenue",
                    "Revenue",
                    height=370,
                    top_n=12,
                ),
                height=370,
            )

    left, right = st.columns([1.35, 1], gap="large")
    with left:
        ui.section("State-wise revenue", "Top customer states by product revenue.")
        if states.empty:
            ui.empty_state("No state revenue", "No item revenue exists for the current selection.")
        else:
            top_states = states.head(12).copy()
            top_states["display"] = top_states["customer_state"] + " · " + top_states["state_name"]
            ui.plot(
                charts.horizontal_bar(
                    top_states,
                    "display",
                    "revenue",
                    "Revenue",
                    height=370,
                    top_n=12,
                    color=COLORS["blue"],
                ),
                height=370,
            )
    with right:
        ui.section("What the data says", "A short readout generated from the current selection.")
        ui.callout(_readout(ctx, k, monthly, categories, states), tone="success", icon="→")
        ui.callout(
            f"Average order value is {format_currency(k['aov'])}. "
            f"The source covers {format_int(k['active_products'])} products and "
            f"{format_int(k['active_sellers'])} sellers in this selection.",
            tone="info",
            icon="i",
        )

    ui.footer_note(ctx.source_path)
