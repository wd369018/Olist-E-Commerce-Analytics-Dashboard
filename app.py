"""Olist E-Commerce Analytics Dashboard — Streamlit entry point.

Run locally with:
    py -m streamlit run app.py
"""
from __future__ import annotations

import streamlit as st

from dashboard import theme, ui
from dashboard.config import APP_TITLE, STATE_NAMES, STATUS_LABELS
from dashboard.context import (
    clear_data_cache,
    database_path,
    date_range_text,
    get_data,
    get_filter_options,
    reset_filters,
)

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="auto",
    menu_items={
        "Get help": None,
        "Report a bug": None,
        "About": "Olist Brazilian E-Commerce Analytics Dashboard. All metrics are calculated locally from Parquet or SQLite data.",
    },
)

ui.inject_css()
ui.theme_control()
theme.sync_native_theme()


def _load_source():
    try:
        path = database_path()
        data = get_data(path)
        options = get_filter_options(path)
        return path, data, options
    except Exception as exc:  # pragma: no cover - exercised only on setup failure
        st.error(
            "The dashboard could not load the Olist datasets.\n\n"
            f"**Details:** `{exc}`\n\n"
            "Confirm that `data/parquet/` contains the converted datasets, or set "
            "`OLIST_DB_PATH` to a non-empty SQLite database."
        )
        st.stop()


db_path, data, options = _load_source()

# Initialise persisted filter defaults once.
st.session_state.setdefault("filter_date_range", (options["min_date"], options["max_date"]))
st.session_state.setdefault("filter_statuses", [])
st.session_state.setdefault("filter_states", [])
st.session_state.setdefault("filter_categories", [])

with st.sidebar:
    ui.sidebar_brand()
    st.markdown('<div class="sidebar-label">Filters</div>', unsafe_allow_html=True)
    st.date_input(
        "Purchase period",
        key="filter_date_range",
        min_value=options["min_date"],
        max_value=options["max_date"],
        format="DD/MM/YYYY",
        help="Pick a start and end date. Filters orders by purchase date, inclusive.",
    )

    status_labels = {status: STATUS_LABELS.get(status, status.title()) for status in options["statuses"]}
    st.multiselect(
        "Order status",
        options=options["statuses"],
        key="filter_statuses",
        format_func=lambda status: status_labels.get(status, status.title()),
        placeholder="All statuses",
        help="Leave empty to include every order status.",
    )
    st.multiselect(
        "Customer state",
        options=options["states"],
        key="filter_states",
        format_func=lambda state: f"{state} · {STATE_NAMES.get(state, state)}",
        placeholder="All states",
        help="Filter orders by the customer's state.",
    )
    st.multiselect(
        "Product category",
        options=options["categories"],
        key="filter_categories",
        format_func=lambda category: category.replace("_", " ").title(),
        placeholder="All categories",
        help=(
            "When active, order counts cover orders containing the category and revenue covers "
            "only the selected category items."
        ),
    )

    button_cols = st.columns(2)
    with button_cols[0]:
        st.button(
            "Reset",
            width="stretch",
            help="Reset all filters",
            on_click=reset_filters,
            args=(options,),
        )
    with button_cols[1]:
        st.button(
            "Reload",
            width="stretch",
            help="Clear cached data and reload the source",
            on_click=clear_data_cache,
        )

    st.markdown('<div class="sidebar-label">Dataset</div>', unsafe_allow_html=True)
    note_html = (
        f'<div class="source-note">'
        f'<strong>Olist Brazilian E-Commerce</strong><br>'
        f'{date_range_text(data)}<br>'
        f'{data["metadata"]["order_count"]:,} orders · {data["metadata"]["review_count"]:,} reviews'
        f'</div>'
    )
    st.markdown(note_html, unsafe_allow_html=True)

    with st.expander("Metric definitions"):
        st.markdown(
            """
            - **Product revenue:** item prices only, excluding freight, on non-canceled orders.
            - **AOV:** product revenue ÷ orders with items (excluding canceled/unavailable).
            - **Cancellation rate:** canceled orders ÷ all orders.
            - **Repeat rate:** customers with 2+ valid orders ÷ customers with 1+ valid order.
            - **Late delivery:** actual delivery date later than the estimate.
            - **Review score:** latest review per order, so each order counts once.
            """
        )

pages = [
    st.Page(
        "dashboard/pages/executive.py",
        title="Executive Overview",
        icon=":material/space_dashboard:",
        default=True,
        url_path="executive",
    ),
    st.Page(
        "dashboard/pages/sales.py",
        title="Sales Analytics",
        icon=":material/trending_up:",
        url_path="sales",
    ),
    st.Page(
        "dashboard/pages/customers.py",
        title="Customer Analytics",
        icon=":material/groups:",
        url_path="customers",
    ),
    st.Page(
        "dashboard/pages/products.py",
        title="Product & Seller",
        icon=":material/inventory_2:",
        url_path="products",
    ),
    st.Page(
        "dashboard/pages/delivery.py",
        title="Delivery Operations",
        icon=":material/local_shipping:",
        url_path="delivery",
    ),
    st.Page(
        "dashboard/pages/satisfaction.py",
        title="Customer Satisfaction",
        icon=":material/sentiment_satisfied:",
        url_path="satisfaction",
    ),
    st.Page(
        "dashboard/pages/payments.py",
        title="Payments Analytics",
        icon=":material/payments:",
        url_path="payments",
    ),
    st.Page(
        "dashboard/pages/data_quality.py",
        title="Data Quality",
        icon=":material/fact_check:",
        url_path="data-quality",
    ),
]

navigation = st.navigation(pages, position="sidebar", expanded=True)
navigation.run()
