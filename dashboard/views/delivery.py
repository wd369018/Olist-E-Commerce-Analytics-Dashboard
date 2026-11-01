"""Delivery operations page."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from .. import charts, metrics, ui
from ..config import COLORS, METRIC_HELP
from ..filters import AnalysisContext
from ..formatting import format_days, format_int, format_pct, safe_div


def render(ctx: AnalysisContext) -> None:
    delivery = metrics.delivery_metrics(ctx)
    by_category = metrics.delivery_by_category(ctx, min_orders=30)

    ui.page_header(
        "Delivery operations",
        "Fulfilment speed, promise reliability and the geographic and category drivers of late delivery.",
        eyebrow="Operations",
    )
    ui.active_filter_bar(ctx)

    cards = [
        {
            "label": "Average delivery time",
            "value": format_days(delivery["avg_delivery_days"]),
            "sub": "Purchase to customer delivery",
            "accent": COLORS["teal"],
            "help": METRIC_HELP["delivery_days"],
        },
        {
            "label": "Median delivery time",
            "value": format_days(delivery["median_delivery_days"]),
            "sub": "Middle delivered order",
            "accent": COLORS["blue"],
        },
        {
            "label": "Late delivery rate",
            "value": format_pct(delivery["late_rate"]),
            "sub": f"{format_int(delivery['late_orders'])} late deliveries",
            "accent": COLORS["red"],
            "help": METRIC_HELP["late_rate"],
        },
        {
            "label": "On-time rate",
            "value": format_pct(delivery["on_time_rate"]),
            "sub": f"{format_int(delivery['on_time_orders'])} on time or early",
            "accent": COLORS["green"],
        },
        {
            "label": "Average delay when late",
            "value": format_days(delivery["avg_late_days"]),
            "sub": "Days beyond the estimate",
            "accent": COLORS["amber"],
        },
        {
            "label": "Average transit time",
            "value": format_days(delivery["avg_transit_days"]),
            "sub": "Carrier handoff to customer",
            "accent": COLORS["violet"],
        },
    ]
    ui.kpi_cards(cards)

    if ctx.orders.empty:
        ui.empty_state()
        ui.footer_note(ctx.source_path)
        return

    monthly = delivery["monthly"]
    if monthly.empty or delivery["delivered_with_valid_dates"] == 0:
        ui.empty_state(
            "No valid delivery dates",
            "The current selection has no delivered orders with usable purchase and delivery timestamps.",
        )
        ui.footer_note(ctx.source_path)
        return

    left, right = st.columns([1.15, 1], gap="large")
    with left:
        ui.section(
            "Delivery speed trend",
            "Bars show delivered order volume; the line shows average days from purchase to delivery.",
        )
        ui.plot(
            charts.dual_metric_trend(
                monthly,
                "purchase_month",
                "delivered",
                "avg_delivery_days",
                "Delivered orders",
                "Avg delivery days",
                bar_kind="number",
                line_kind="days",
                height=380,
            ),
            height=380,
        )
    with right:
        ui.section(
            "Late delivery rate trend",
            "Share of delivered orders that missed the estimated delivery date.",
        )
        ui.plot(
            charts.line_chart(
                monthly,
                "purchase_month",
                "late_rate",
                "Late delivery rate",
                kind="percent",
                color=COLORS["red"],
                height=380,
                fill=True,
            ),
            height=380,
        )

    left, right = st.columns([1, 1.15], gap="large")
    with left:
        ui.section("Delivery time distribution", "Delivered orders with valid dates.")
        valid_days = ctx.orders[
            ctx.orders["is_delivered"]
            & ctx.orders["delivered_ts"].notna()
            & ctx.orders["delivery_days"].ge(0)
        ]["delivery_days"]
        ui.plot(
            charts.histogram(
                valid_days,
                "Delivery days",
                height=390,
                nbins=50,
                kind="days",
                color="rgba(37,99,235,.62)",
            ),
            height=390,
        )
    with right:
        ui.section(
            "Late rate by state",
            "States with at least 30 delivered orders and valid estimates. Higher bars need attention.",
        )
        state_late = delivery["late_by_state"]
        state_late = state_late[state_late["delivered"] >= 30].head(15).copy()
        if state_late.empty:
            ui.empty_state("Not enough state-level deliveries", "No state has 30+ valid delivered orders.")
        else:
            state_late["display"] = state_late["customer_state"] + " · " + state_late["state_name"]
            state_late = state_late.sort_values("late_rate", ascending=True)
            ui.plot(
                charts.horizontal_bar(
                    state_late,
                    "display",
                    "late_rate",
                    "Late rate",
                    height=390,
                    kind="percent",
                    color=COLORS["red"],
                ),
                height=390,
            )

    stages = ctx.orders[
        ctx.orders["is_delivered"]
        & ctx.orders["delivery_days"].ge(0)
        & ctx.orders["carrier_days"].ge(0)
        & ctx.orders["transit_days"].ge(0)
    ]
    if not stages.empty:
        carrier_share = (
            safe_div(stages["carrier_days"].median(), stages["delivery_days"].median()) * 100
        )
        ui.callout(
            f"Median carrier handoff takes {format_days(stages['carrier_days'].median())} and median "
            f"last-mile transit takes {format_days(stages['transit_days'].median())}. "
            f"Carrier handoff accounts for about {format_pct(carrier_share)} of the median total delivery time.",
            tone="info",
            icon="i",
        )

    ui.section(
        "Late delivery by category",
        "Categories with 30+ delivered orders. Orders containing multiple categories are attributed to each category.",
    )
    if by_category.empty:
        ui.empty_state("Not enough category-level deliveries", "No category has 30+ valid delivered orders.")
    else:
        lowest = by_category.sort_values("late_rate", ascending=False).head(15).copy()
        lowest["display"] = lowest["category"].str.replace("_", " ").str.title()
        lowest = lowest.sort_values("late_rate", ascending=True)
        ui.plot(
            charts.horizontal_bar(
                lowest,
                "display",
                "late_rate",
                "Late rate",
                height=420,
                kind="percent",
                color=COLORS["amber"],
            ),
            height=420,
        )

    ui.section("State delivery table", "Late-delivery performance for states with 30+ valid delivered orders.")
    state_table = delivery["late_by_state"].copy()
    state_table = state_table[state_table["delivered"] >= 30].sort_values("late_rate", ascending=False)
    state_table = state_table[["customer_state", "state_name", "delivered", "late_orders", "late_rate"]]
    state_table.columns = ["State", "State name", "Delivered", "Late orders", "Late rate"]
    ui.show_table(
        state_table,
        column_config={"Late rate": st.column_config.NumberColumn(format="%.1f%%")},
        height=400,
    )
    ui.download_csv(state_table, "olist_delivery_by_state.csv", "Download delivery table")

    summary = (
        f"{format_int(delivery['delivered_with_valid_dates'])} of "
        f"{format_int(delivery['delivered_orders'])} delivered orders have valid dates "
        f"({format_pct(delivery['delivery_coverage'])} coverage). "
        f"{format_int(delivery['delivered_missing_delivery_date'])} delivered orders are missing a delivery timestamp."
    )
    ui.callout(summary, tone="warning" if delivery["delivered_missing_delivery_date"] else "success", icon="i")

    ui.footer_note(ctx.source_path)
