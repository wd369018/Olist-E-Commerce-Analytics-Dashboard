"""Sales analytics page."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from .. import charts, metrics, ui
from ..config import COLORS, METRIC_HELP
from ..filters import AnalysisContext
from ..formatting import format_currency, format_int, format_number, format_pct


def render(ctx: AnalysisContext) -> None:
    k = metrics.overview_metrics(ctx)
    monthly = metrics.monthly_sales(ctx)
    categories = metrics.category_performance(ctx)
    states = metrics.state_performance(ctx)
    trend, trend_categories = metrics.monthly_category_trend(ctx, top_n=6)

    ui.page_header(
        "Sales analytics",
        "Revenue quality, momentum, category contribution and geographic concentration.",
        eyebrow="Commercial performance",
    )
    ui.active_filter_bar(ctx)

    top_category = categories.iloc[0]["category"] if not categories.empty else "—"
    latest = monthly.iloc[-1] if not monthly.empty else None
    latest_growth = latest["mom_growth"] if latest is not None else float("nan")
    cards = [
        {
            "label": "Product revenue",
            "value": format_currency(k["product_revenue"], compact=True),
            "sub": f"Gross incl. freight {format_currency(k['gross_revenue'], compact=True)}",
            "accent": COLORS["teal"],
            "help": METRIC_HELP["product_revenue"],
        },
        {
            "label": "Orders",
            "value": format_int(k["total_orders"]),
            "sub": f"{format_int(k['orders_with_items'])} include items",
            "accent": COLORS["blue"],
            "help": METRIC_HELP["total_orders"],
        },
        {
            "label": "Average order value",
            "value": format_currency(k["aov"]),
            "sub": "Product revenue per order with items",
            "accent": COLORS["violet"],
            "help": METRIC_HELP["aov"],
        },
        {
            "label": "Top category",
            "value": top_category.replace("_", " ").title() if top_category != "—" else "—",
            "sub": (
                f"{format_currency(categories.iloc[0]['revenue'], compact=True)} · "
                f"{format_pct(categories.iloc[0]['revenue_share'])} share"
                if not categories.empty
                else "No category revenue"
            ),
            "accent": COLORS["amber"],
        },
        {
            "label": "Latest month revenue",
            "value": format_currency(latest["revenue"], compact=True) if latest is not None else "—",
            "sub": latest["month_label"] if latest is not None else "No data",
            "accent": COLORS["green"],
            "delta": (
                f"{latest_growth:+.1f}% vs previous month"
                if latest is not None and pd.notna(latest_growth)
                else None
            ),
            "delta_tone": (
                "pos" if latest is not None and pd.notna(latest_growth) and latest_growth >= 0 else "neg"
            ),
        },
    ]
    ui.kpi_cards(cards)

    if ctx.orders.empty:
        ui.empty_state()
        ui.footer_note(ctx.source_path)
        return

    ui.section(
        "Monthly revenue and order trend",
        "Bars show order volume; the line shows product revenue. The source's final months are partial.",
    )
    if monthly.empty:
        ui.empty_state("No monthly data", "No orders match the current filters.")
    else:
        ui.plot(charts.revenue_orders_trend(monthly), height=390)

    ui.section(
        "Category contribution",
        "Revenue is based on item prices. Click or hover to explore the largest categories.",
    )
    if categories.empty:
        ui.empty_state("No category data", "No item revenue exists for the current selection.")
    else:
        left, right = st.columns([1.15, 1], gap="large")
        with left:
            ui.plot(charts.treemap(categories.head(24), "category", "revenue", height=400), height=400)
        with right:
            top = categories.head(12).copy()
            top["display"] = top["category"].str.replace("_", " ").str.title()
            ui.plot(
                charts.horizontal_bar(
                    top,
                    "display",
                    "revenue",
                    "Revenue",
                    height=400,
                    color=COLORS["blue"],
                ),
                height=400,
            )

    if not trend.empty and trend_categories:
        ui.section(
            "Category mix over time",
            "Monthly product revenue for the six largest categories, with all others grouped as Other.",
        )
        labels = [category.replace("_", " ").title() for category in trend_categories]
        ui.plot(
            charts.stacked_area(trend, "purchase_month", trend_categories, labels=labels, height=390),
            height=390,
        )

    left, right = st.columns([1.2, 1], gap="large")
    with left:
        ui.section("State-wise sales", "Product revenue and customer concentration by state.")
        if states.empty:
            ui.empty_state("No state data", "No item revenue exists for the current selection.")
        else:
            top_states = states.head(15).copy()
            top_states["display"] = top_states["customer_state"] + " · " + top_states["state_name"]
            ui.plot(
                charts.horizontal_bar(
                    top_states,
                    "display",
                    "revenue",
                    "Revenue",
                    height=420,
                    color=COLORS["teal"],
                ),
                height=420,
            )
    with right:
        ui.section("Commercial insights", "Generated from the current filtered data.")
        if not categories.empty and categories["revenue"].sum() > 0:
            top_five_share = (
                categories.head(5)["revenue"].sum() / categories["revenue"].sum() * 100
            )
            ui.callout(
                f"The five largest categories generate {format_pct(top_five_share)} of product revenue. "
                f"{categories.iloc[0]['category'].replace('_', ' ').title()} leads with "
                f"{format_currency(categories.iloc[0]['revenue'], compact=True)}.",
                tone="success",
                icon="→",
            )
        if not states.empty and states["revenue"].sum() > 0:
            top_three_share = (
                states.head(3)["revenue"].sum() / states["revenue"].sum() * 100
            )
            ui.callout(
                f"The top three states contribute {format_pct(top_three_share)} of revenue. "
                f"{states.iloc[0]['state_name']} alone contributes {format_pct(states.iloc[0]['revenue_share'])}.",
                tone="info",
                icon="i",
            )
        else:
            ui.callout(
                "No product revenue exists for the current selection, so revenue concentration "
                "cannot be calculated. Order and payment counts may still be present.",
                tone="warning",
                icon="!",
            )
        if latest is not None and pd.notna(latest_growth):
            direction = "grew" if latest_growth >= 0 else "declined"
            ui.callout(
                f"Latest month ({latest['month_label']}) revenue {direction} "
                f"{format_pct(abs(latest_growth))} versus the previous month. "
                "The final source months are incomplete, so treat the last point as provisional.",
                tone="warning",
                icon="!",
            )

    ui.section("Category performance table", "Sortable metrics for every category in the selection.")
    if categories.empty:
        ui.empty_state("No category data", "No item revenue exists for the current selection.")
    else:
        cat_table = categories[
            [
                "category",
                "revenue",
                "revenue_share",
                "items",
                "orders",
                "avg_price",
                "avg_review",
                "late_rate",
            ]
        ].copy()
        cat_table["category"] = cat_table["category"].str.replace("_", " ").str.title()
        cat_table.columns = [
            "Category",
            "Revenue",
            "Revenue share",
            "Items",
            "Orders",
            "Avg item price",
            "Avg review",
            "Late rate",
        ]
        ui.show_table(
            cat_table,
            column_config={
                "Revenue": st.column_config.NumberColumn(format="R$ %.2f"),
                "Revenue share": st.column_config.NumberColumn(format="%.1f%%"),
                "Avg item price": st.column_config.NumberColumn(format="R$ %.2f"),
                "Avg review": st.column_config.NumberColumn(format="%.2f"),
                "Late rate": st.column_config.NumberColumn(format="%.1f%%"),
            },
            height=430,
        )
        ui.download_csv(
            cat_table, "olist_category_performance.csv", "Download category table"
        )

    ui.section("State performance table", "Revenue, order value, delivery and satisfaction by state.")
    if states.empty:
        ui.empty_state("No state data", "No orders match the current filters.")
    else:
        state_table = states[
            [
                "customer_state",
                "state_name",
                "revenue",
                "revenue_share",
                "orders",
                "avg_order_value",
                "late_rate",
                "avg_review",
            ]
        ].copy()
        state_table.columns = [
            "State",
            "State name",
            "Revenue",
            "Revenue share",
            "Orders",
            "Avg order value",
            "Late rate",
            "Avg review",
        ]
        ui.show_table(
            state_table,
            column_config={
                "Revenue": st.column_config.NumberColumn(format="R$ %.2f"),
                "Revenue share": st.column_config.NumberColumn(format="%.1f%%"),
                "Avg order value": st.column_config.NumberColumn(format="R$ %.2f"),
                "Late rate": st.column_config.NumberColumn(format="%.1f%%"),
                "Avg review": st.column_config.NumberColumn(format="%.2f"),
            },
            height=430,
        )
        ui.download_csv(state_table, "olist_state_performance.csv", "Download state table")

    ui.footer_note(ctx.source_path)
