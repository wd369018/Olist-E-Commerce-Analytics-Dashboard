"""Customer analytics page."""
from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from .. import charts, metrics, ui
from ..config import COLORS, METRIC_HELP
from ..filters import AnalysisContext
from ..formatting import format_currency, format_int, format_number, format_pct


def render(ctx: AnalysisContext) -> None:
    k = metrics.overview_metrics(ctx)
    customers = metrics.customer_frame(ctx)
    segments = metrics.segment_summary(customers)
    frequency = metrics.purchase_frequency(customers)
    new_returning = metrics.new_returning_monthly(ctx)
    states = metrics.customer_state_summary(customers)

    ui.page_header(
        "Customer analytics",
        "Retention, purchase frequency and value-based segmentation of the customer base.",
        eyebrow="Customer intelligence",
    )
    ui.active_filter_bar(ctx)

    avg_items = float(customers["items"].mean()) if not customers.empty else float("nan")
    cards = [
        {
            "label": "Unique customers",
            "value": format_int(k["unique_customers"]),
            "sub": "Verified customer profiles",
            "accent": COLORS["teal"],
        },
        {
            "label": "Repeat customers",
            "value": format_int(k["repeat_customers"]),
            "sub": f"{format_pct(k['repeat_rate'])} repeat rate",
            "accent": COLORS["blue"],
            "help": METRIC_HELP["repeat_rate"],
        },
        {
            "label": "Repeat customer rate",
            "value": format_pct(k["repeat_rate"]),
            "sub": "2+ valid orders / all customers",
            "accent": COLORS["green"],
            "help": METRIC_HELP["repeat_rate"],
        },
        {
            "label": "Orders per customer",
            "value": format_number(k["avg_orders_per_customer"], 2),
            "sub": "Average across valid orders",
            "accent": COLORS["violet"],
        },
        {
            "label": "Customer value",
            "value": format_currency(k["avg_customer_value"]),
            "sub": "Product revenue per customer",
            "accent": COLORS["amber"],
        },
        {
            "label": "Items per customer",
            "value": format_number(avg_items, 2),
            "sub": "Average item rows purchased",
            "accent": COLORS["slate"],
        },
    ]
    ui.kpi_cards(cards)

    if customers.empty:
        ui.empty_state("No customers in this selection", "Widen the filters to see customer analytics.")
        ui.footer_note(ctx.source_path)
        return

    left, right = st.columns([1, 1], gap="large")
    with left:
        ui.section("Purchase frequency", "How many valid orders each customer placed.")
        ui.plot(
            charts.vertical_bar(
                frequency,
                "frequency_bucket",
                "customers",
                "Customers",
                kind="number",
                color=COLORS["teal"],
                height=350,
                category_order=frequency["frequency_bucket"].tolist(),
            ),
            height=350,
        )
    with right:
        ui.section("RFM segments", "Recency, frequency and monetary value ranking.")
        ui.plot(
            charts.donut(
                segments["segment"],
                segments["customers"],
                center_text=format_int(len(customers)),
                height=350,
            ),
            height=350,
        )

    ui.section(
        "New versus returning customers",
        "Customers are classified as new in their first purchase month and returning thereafter.",
    )
    if new_returning.empty:
        ui.empty_state("No customer trend", "No valid orders match the current filters.")
    else:
        ui.plot(
            charts.stacked_bar(
                new_returning,
                "purchase_month",
                ["new_customers", "returning_customers"],
                labels=["New customers", "Returning customers"],
                height=370,
            ),
            height=370,
        )

    left, right = st.columns([1.15, 1], gap="large")
    with left:
        ui.section("Customers by state", "Unique customers and revenue by customer state.")
        top_states = states.head(15).copy()
        top_states["display"] = top_states["customer_state"] + " · " + top_states["state_name"]
        ui.plot(
            charts.horizontal_bar(
                top_states,
                "display",
                "customers",
                "Customers",
                height=420,
                kind="number",
                color=COLORS["blue"],
            ),
            height=420,
        )
    with right:
        ui.section("Customer value distribution", "Product revenue per customer, clipped at the 99th percentile.")
        clipped = customers["monetary"].clip(
            lower=0, upper=float(customers["monetary"].quantile(0.99))
        )
        ui.plot(
            charts.histogram(
                clipped,
                "Customer revenue",
                height=420,
                nbins=40,
                kind="currency",
                color="rgba(124,58,237,.65)",
            ),
            height=420,
        )

    ui.section("Segment performance", "Customer count and revenue contribution by RFM segment.")
    segment_table = segments.copy()
    segment_table.columns = [
        "Segment",
        "Customers",
        "Customer share",
        "Revenue",
        "Revenue share",
        "Avg customer value",
    ]
    ui.show_table(
        segment_table,
        column_config={
            "Customer share": st.column_config.NumberColumn(format="%.1f%%"),
            "Revenue": st.column_config.NumberColumn(format="R$ %.2f"),
            "Revenue share": st.column_config.NumberColumn(format="%.1f%%"),
            "Avg customer value": st.column_config.NumberColumn(format="R$ %.2f"),
        },
        height=300,
    )

    if not segments.empty:
        champion_share = segments.loc[segments["segment"].eq("Champions"), "revenue_share"].sum()
        top_segment = segments.iloc[0]
        ui.callout(
            f"{top_segment['segment']} is the largest revenue segment at "
            f"{format_currency(top_segment['revenue'], compact=True)} "
            f"({format_pct(top_segment['revenue_share'])} of revenue). "
            f"Champions contribute {format_pct(champion_share)} of customer revenue.",
            tone="success",
            icon="→",
        )
        if k["repeat_rate"] < 5:
            ui.callout(
                f"Repeat purchasing is low ({format_pct(k['repeat_rate'])}). "
                "The marketplace is acquisition-heavy; retention campaigns have meaningful upside.",
                tone="warning",
                icon="!",
            )

    ui.section("Top customers", "Highest-value customers in the current selection.")
    top_customers = customers.head(50).copy()
    top_customers["customer_unique_id"] = top_customers["customer_unique_id"].astype(str).str[:14] + "…"
    top_customers = top_customers[
        [
            "customer_unique_id",
            "customer_state",
            "frequency",
            "monetary",
            "avg_order_value",
            "recency_days",
            "last_purchase",
            "segment",
        ]
    ].copy()
    top_customers.columns = [
        "Customer ID",
        "State",
        "Orders",
        "Revenue",
        "Avg order value",
        "Recency (days)",
        "Last purchase",
        "Segment",
    ]
    ui.show_table(
        top_customers,
        column_config={
            "Revenue": st.column_config.NumberColumn(format="R$ %.2f"),
            "Avg order value": st.column_config.NumberColumn(format="R$ %.2f"),
            "Last purchase": st.column_config.DateColumn(format="DD MMM YYYY"),
        },
        height=420,
    )
    ui.download_csv(top_customers, "olist_top_customers.csv", "Download top customers")

    ui.footer_note(ctx.source_path)
