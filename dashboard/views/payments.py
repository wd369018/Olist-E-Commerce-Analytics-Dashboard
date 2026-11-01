"""Payments analytics page."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from .. import charts, metrics, ui
from ..config import COLORS, PAYMENT_LABELS
from ..filters import AnalysisContext
from ..formatting import format_currency, format_int, format_number, format_pct


def render(ctx: AnalysisContext) -> None:
    payment = metrics.payment_metrics(ctx)

    ui.page_header(
        "Payments analytics",
        "Payment methods, installment behaviour, transaction values and order-level reconciliation.",
        eyebrow="Financial flows",
    )
    ui.active_filter_bar(ctx)

    methods = payment["methods"]
    top_label = PAYMENT_LABELS.get(str(payment["top_method"]), str(payment["top_method"]))
    cards = [
        {
            "label": "Total payment value",
            "value": format_currency(payment["payment_total"], compact=True),
            "sub": f"{format_int(payment['orders_with_payment'])} orders with payments",
            "accent": COLORS["teal"],
        },
        {
            "label": "Average payment / order",
            "value": format_currency(payment["avg_payment"]),
            "sub": "All payment records per order",
            "accent": COLORS["blue"],
        },
        {
            "label": "Top payment method",
            "value": top_label,
            "sub": f"{format_currency(payment['top_method_value'], compact=True)} total value",
            "accent": COLORS["violet"],
        },
        {
            "label": "Average installments",
            "value": format_number(payment["avg_installments"], 1),
            "sub": f"Up to {format_int(payment['max_installments'])} installments",
            "accent": COLORS["amber"],
        },
        {
            "label": "Installment orders",
            "value": format_pct(payment["installment_order_share"]),
            "sub": "Orders with 2+ installments",
            "accent": COLORS["green"],
        },
        {
            "label": "Zero-value records",
            "value": format_int(payment["zero_value_records"]),
            "sub": "Payment records with value ≤ 0",
            "accent": COLORS["slate"],
        },
    ]
    ui.kpi_cards(cards)

    if ctx.payments.empty:
        ui.empty_state("No payments in this selection", "Widen the filters to analyse payments.")
        ui.footer_note(ctx.source_path)
        return

    left, right = st.columns([1, 1.2], gap="large")
    with left:
        ui.section("Payment method mix", "Share of total payment value.")
        method_labels = methods["payment_type"].map(lambda value: PAYMENT_LABELS.get(value, value))
        ui.plot(
            charts.donut(
                method_labels,
                methods["value"],
                center_text=format_currency(payment["payment_total"], compact=True),
                height=360,
            ),
            height=360,
        )
    with right:
        ui.section("Method comparison", "Payment records and value by method.")
        method_table = methods.copy()
        method_table["method"] = method_table["payment_type"].map(
            lambda value: PAYMENT_LABELS.get(value, value)
        )
        method_table = method_table[["method", "records", "orders", "value", "share_value", "avg_value", "avg_installments"]]
        method_table.columns = ["Method", "Records", "Orders", "Value", "Value share", "Avg value", "Avg installments"]
        ui.show_table(
            method_table,
            column_config={
                "Value": st.column_config.NumberColumn(format="R$ %.2f"),
                "Value share": st.column_config.NumberColumn(format="%.1f%%"),
                "Avg value": st.column_config.NumberColumn(format="R$ %.2f"),
                "Avg installments": st.column_config.NumberColumn(format="%.1f"),
            },
            height=300,
        )

    if not payment["monthly"].empty:
        ui.section(
            "Payment value trend",
            "Monthly payment value for the five largest methods. Vouchers and partial payments remain separate.",
        )
        method_monthly = payment["method_monthly"]
        value_columns = [
            column
            for column in method_monthly.columns
            if column not in {"purchase_month", "month_label"}
        ]
        if value_columns:
            ui.plot(
                charts.stacked_area(
                    method_monthly,
                    "purchase_month",
                    value_columns,
                    labels=[PAYMENT_LABELS.get(column, column) for column in value_columns],
                    height=390,
                ),
                height=390,
            )

    left, right = st.columns([1.15, 1], gap="large")
    with left:
        ui.section("Installment distribution", "Orders by maximum number of installments, with average order value.")
        if payment["installments"].empty:
            ui.empty_state("No installment data", "No payment installments match the current filters.")
        else:
            ui.plot(charts.installments_chart(payment["installments"], height=390), height=390)
    with right:
        ui.section("Order payment distribution", "Order-level payment value, clipped at the 99th percentile.")
        order_values = ctx.orders.loc[ctx.orders["payment_records"].gt(0), "payment_value"]
        clipped = order_values.clip(lower=0, upper=float(order_values.quantile(0.99)))
        ui.plot(
            charts.histogram(
                clipped,
                "Payment value",
                height=390,
                nbins=45,
                kind="currency",
                color="rgba(245,158,11,.62)",
            ),
            height=390,
        )

    reconciliation = payment["reconciliation"]
    if reconciliation:
        tone = "success" if reconciliation["mismatches"] == 0 else "warning"
        share = reconciliation["mismatch_rate"]
        ui.callout(
            f"Reconciliation: item price + freight versus payment value for "
            f"{format_int(reconciliation['orders_checked'])} orders with both records. "
            f"{format_int(reconciliation['mismatches'])} orders ({format_pct(share)}) differ by more than R$ 0.01; "
            f"total absolute difference is {format_currency(reconciliation['absolute_difference'])}. "
            "Some differences are expected from vouchers, rounding and payment sequencing.",
            tone=tone,
            icon="✓" if reconciliation["mismatches"] == 0 else "!",
        )
    elif ctx.filters.categories:
        ui.callout(
            "Order-level payment reconciliation is unavailable while a category filter is active because "
            "payment values cover full orders, while item revenue is restricted to the selected categories.",
            tone="info",
            icon="i",
        )

    ui.section("Payment details", "One row per payment method in the current selection.")
    detail = methods[
        ["payment_type", "records", "orders", "value", "share_value", "avg_value", "avg_installments"]
    ].copy()
    detail["payment_type"] = detail["payment_type"].map(lambda value: PAYMENT_LABELS.get(value, value))
    detail.columns = ["Method", "Records", "Orders", "Value", "Value share", "Avg value", "Avg installments"]
    ui.show_table(
        detail,
        column_config={
            "Value": st.column_config.NumberColumn(format="R$ %.2f"),
            "Value share": st.column_config.NumberColumn(format="%.1f%%"),
            "Avg value": st.column_config.NumberColumn(format="R$ %.2f"),
            "Avg installments": st.column_config.NumberColumn(format="%.1f"),
        },
        height=280,
    )
    ui.download_csv(detail, "olist_payment_methods.csv", "Download payment table")

    ui.footer_note(ctx.source_path)
