"""Product and seller analytics page."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from .. import charts, metrics, ui
from ..config import COLORS
from ..filters import AnalysisContext
from ..formatting import format_currency, format_int, format_number, format_pct, safe_div


def render(ctx: AnalysisContext) -> None:
    k = metrics.overview_metrics(ctx)
    categories = metrics.category_performance(ctx)
    products = metrics.top_products(ctx, limit=50)
    sellers = metrics.seller_performance(ctx)
    seller_states = metrics.seller_state_summary(ctx)

    ui.page_header(
        "Product & seller analytics",
        "Category economics, product-level performance and marketplace seller concentration.",
        eyebrow="Catalogue and partners",
    )
    ui.active_filter_bar(ctx)

    avg_item_price = (
        float(ctx.valid_items["price"].mean()) if not ctx.valid_items.empty else float("nan")
    )
    top_seller_share = (
        safe_div(sellers.head(10)["revenue"].sum(), sellers["revenue"].sum()) * 100
        if not sellers.empty
        else 0.0
    )
    cards = [
        {
            "label": "Active categories",
            "value": format_int(k["active_categories"]),
            "sub": "Categories with item revenue",
            "accent": COLORS["teal"],
        },
        {
            "label": "Products sold",
            "value": format_int(k["active_products"]),
            "sub": "Active catalog products",
            "accent": COLORS["blue"],
        },
        {
            "label": "Active sellers",
            "value": format_int(k["active_sellers"]),
            "sub": "Active marketplace merchants",
            "accent": COLORS["violet"],
        },
        {
            "label": "Average item price",
            "value": format_currency(avg_item_price),
            "sub": "Item price, excluding freight",
            "accent": COLORS["amber"],
        },
        {
            "label": "Top-10 seller share",
            "value": format_pct(top_seller_share),
            "sub": "Revenue concentration",
            "accent": COLORS["red"],
        },
        {
            "label": "Items per order",
            "value": format_number(
                ctx.valid_items.groupby("order_id").size().mean()
                if not ctx.valid_items.empty
                else float("nan"),
                2,
            ),
            "sub": "Average item rows per order",
            "accent": COLORS["slate"],
        },
    ]
    ui.kpi_cards(cards)

    if ctx.valid_items.empty:
        ui.empty_state("No item data in this selection", "Widen the filters to analyse products and sellers.")
        ui.footer_note(ctx.source_path)
        return

    left, right = st.columns([1.2, 1], gap="large")
    with left:
        ui.section("Category revenue", "Top 15 categories by product revenue.")
        top = categories.head(15).copy()
        top["display"] = top["category"].str.replace("_", " ").str.title()
        ui.plot(
            charts.horizontal_bar(
                top,
                "display",
                "revenue",
                "Revenue",
                height=440,
                color=COLORS["teal"],
            ),
            height=440,
        )
    with right:
        ui.section("Seller footprint by state", "Seller revenue and seller counts by state.")
        top_states = seller_states.head(15).copy()
        top_states["display"] = top_states["seller_state"] + " · " + top_states["state_name"]
        ui.plot(
            charts.horizontal_bar(
                top_states,
                "display",
                "revenue",
                "Seller revenue",
                height=440,
                color=COLORS["blue"],
            ),
            height=440,
        )

    ui.section(
        "Top products",
        "Product performance and order volume by catalog product ID.",
    )
    product_table = products.head(30).copy()
    product_table["product_id"] = product_table["product_id"].astype(str).str[:14] + "…"
    product_table["category"] = product_table["category"].str.replace("_", " ").str.title()
    product_table = product_table[
        ["product_id", "category", "revenue", "units", "orders", "avg_price", "sellers", "last_sale"]
    ].copy()
    product_table.columns = [
        "Product ID",
        "Category",
        "Revenue",
        "Units",
        "Orders",
        "Avg price",
        "Sellers",
        "Last sale",
    ]
    ui.show_table(
        product_table,
        column_config={
            "Revenue": st.column_config.NumberColumn(format="R$ %.2f"),
            "Avg price": st.column_config.NumberColumn(format="R$ %.2f"),
            "Last sale": st.column_config.DateColumn(format="DD MMM YYYY"),
        },
        height=430,
    )
    ui.download_csv(product_table, "olist_top_products.csv", "Download product table")

    left, right = st.columns([1.1, 1], gap="large")
    with left:
        ui.section(
            "Seller concentration",
            "Cumulative revenue share by seller rank. A steep curve indicates dependence on a few sellers.",
        )
        ui.plot(charts.pareto_chart(sellers, "Seller", "revenue", height=380), height=380)
    with right:
        ui.section("Top sellers", "Highest-revenue sellers in the selection.")
        top_sellers = sellers.head(12).copy()
        top_sellers["display"] = top_sellers["seller_id"].astype(str).str[:10] + "… · " + top_sellers["seller_state"]
        ui.plot(
            charts.horizontal_bar(
                top_sellers,
                "display",
                "revenue",
                "Revenue",
                height=380,
                color=COLORS["violet"],
            ),
            height=380,
        )

    ui.section(
        "Seller performance",
        "Revenue, order reach and late-delivery rate. Late rate is based on distinct orders containing the seller.",
    )
    seller_table = sellers.head(100).copy()
    seller_table["seller_id"] = seller_table["seller_id"].astype(str).str[:14] + "…"
    seller_table = seller_table[
        [
            "seller_id",
            "seller_city",
            "seller_state",
            "revenue",
            "items",
            "orders",
            "products",
            "avg_item_price",
            "revenue_share",
            "delivered_orders",
            "late_rate",
        ]
    ].copy()
    seller_table.columns = [
        "Seller ID",
        "City",
        "State",
        "Revenue",
        "Items",
        "Orders",
        "Products",
        "Avg item price",
        "Revenue share",
        "Delivered orders",
        "Late rate",
    ]
    ui.show_table(
        seller_table,
        column_config={
            "Revenue": st.column_config.NumberColumn(format="R$ %.2f"),
            "Avg item price": st.column_config.NumberColumn(format="R$ %.2f"),
            "Revenue share": st.column_config.NumberColumn(format="%.1f%%"),
            "Late rate": st.column_config.NumberColumn(format="%.1f%%"),
        },
        height=430,
    )
    ui.download_csv(seller_table, "olist_seller_performance.csv", "Download seller table")

    ui.section("Category economics", "Revenue, product breadth and customer satisfaction by category.")
    category_table = categories.copy()
    category_table["category"] = category_table["category"].str.replace("_", " ").str.title()
    category_table = category_table[
        [
            "category",
            "revenue",
            "revenue_share",
            "items",
            "orders",
            "products",
            "sellers",
            "avg_price",
            "avg_review",
            "late_rate",
        ]
    ].copy()
    category_table.columns = [
        "Category",
        "Revenue",
        "Revenue share",
        "Items",
        "Orders",
        "Products",
        "Sellers",
        "Avg price",
        "Avg review",
        "Late rate",
    ]
    ui.show_table(
        category_table,
        column_config={
            "Revenue": st.column_config.NumberColumn(format="R$ %.2f"),
            "Revenue share": st.column_config.NumberColumn(format="%.1f%%"),
            "Avg price": st.column_config.NumberColumn(format="R$ %.2f"),
            "Avg review": st.column_config.NumberColumn(format="%.2f"),
            "Late rate": st.column_config.NumberColumn(format="%.1f%%"),
        },
        height=430,
    )

    if not sellers.empty:
        top_seller = sellers.iloc[0]
        ui.callout(
            f"The top 10 sellers generate {format_pct(top_seller_share)} of seller revenue. "
            f"The largest seller is {str(top_seller['seller_id'])[:10]}… in {top_seller['seller_state']} "
            f"with {format_currency(top_seller['revenue'], compact=True)}.",
            tone="success",
            icon="→",
        )

    ui.footer_note(ctx.source_path)
