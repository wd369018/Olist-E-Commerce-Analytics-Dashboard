"""Data quality page."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from .. import charts, ui
from ..config import COLORS
from ..context import database_path, get_quality_report
from ..filters import AnalysisContext
from ..formatting import format_int, format_pct


def render(ctx: AnalysisContext) -> None:
    report = get_quality_report(database_path())
    summary = report["summary"]
    profiles = report["profiles"]
    missing = report["missing"]
    invalid_dates = report["invalid_dates"]
    integrity = report["integrity"]
    duplicates = report["duplicates"]
    coverage = report["coverage"]

    ui.page_header(
        "Data quality",
        "Source-wide validation of missing values, duplicates, date anomalies and referential integrity. "
        "These checks are independent of the sidebar filters.",
        eyebrow="Trust and validation",
    )

    cards = [
        {
            "label": "Rows profiled",
            "value": format_int(summary["rows_profiled"]),
            "sub": f"Across {summary['tables_profiled']} modelled tables",
            "accent": COLORS["teal"],
        },
        {
            "label": "Missing cells",
            "value": format_int(summary["missing_cells"]),
            "sub": "Null, blank or sentinel values",
            "accent": COLORS["amber"],
        },
        {
            "label": "Duplicate rows",
            "value": format_int(summary["duplicate_rows"]),
            "sub": "Fully duplicated source rows",
            "accent": COLORS["violet"],
        },
        {
            "label": "Duplicate key issues",
            "value": format_int(summary["duplicate_key_issues"]),
            "sub": "Critical key collisions",
            "accent": COLORS["red"],
        },
        {
            "label": "Invalid date records",
            "value": format_int(summary["invalid_date_records"]),
            "sub": "Impossible or missing date sequences",
            "accent": COLORS["red"],
        },
        {
            "label": "Orphan records",
            "value": format_int(summary["orphan_records"]),
            "sub": "Failed foreign-key relationships",
            "accent": COLORS["green"] if summary["orphan_records"] == 0 else COLORS["red"],
        },
    ]
    ui.kpi_cards(cards)

    if summary["orphan_records"] == 0:
        ui.callout(
            "All critical foreign-key relationships are intact: every order, item, payment and review "
            "points to an existing parent record. One warning remains for product categories that have no "
            "English translation; these are displayed with a readable fallback label.",
            tone="success",
            icon="✓",
        )
    else:
        ui.callout(
            f"{format_int(summary['orphan_records'])} orphan records were found. Review the "
            "referential integrity table before using the affected metrics.",
            tone="danger",
            icon="!",
        )
    ui.callout(
        "The processed database uses the text value '0' for some missing dates, product categories and "
        "review comments. Those values are treated as missing in this report and coerced to null dates "
        "before analysis. Reviews are deduplicated to the latest review per order.",
        tone="info",
        icon="i",
    )

    overview, miss_tab, dates_tab, integrity_tab = st.tabs(
        ["Overview", "Missing values", "Invalid dates", "Integrity & duplicates"]
    )

    with overview:
        ui.section(
            "Table profile",
            "Missing cells include nulls, blanks and sentinel '0' values in text fields. Duplicate keys are "
            "shown separately because some duplicates are legitimate (customer_unique_id).",
        )
        table = profiles.copy()
        table.columns = [
            "Table",
            "Rows",
            "Columns",
            "Cells",
            "Missing cells",
            "Missing %",
            "Duplicate rows",
            "Duplicate keys",
        ]
        ui.show_table(
            table,
            column_config={
                "Missing %": st.column_config.NumberColumn(format="%.2f%%"),
            },
            height=370,
        )
        ui.download_csv(table, "olist_data_quality_profile.csv", "Download profile")

        left, right = st.columns([1.1, 1], gap="large")
        with left:
            ui.section("Missing cells by table", "Absolute count of missing or sentinel cells.")
            missing_table = profiles[profiles["missing_cells"] > 0].copy()
            if missing_table.empty:
                ui.callout("No missing cells detected in the modelled tables.", tone="success", icon="✓")
            else:
                missing_table = missing_table.sort_values("missing_cells", ascending=True)
                ui.plot(
                    charts.horizontal_bar(
                        missing_table,
                        "table",
                        "missing_cells",
                        "Missing cells",
                        height=360,
                        kind="number",
                        color=COLORS["amber"],
                    ),
                    height=360,
                )
        with right:
            ui.section("Coverage gaps", "Orders and customers without expected child records.")
            coverage_table = coverage.copy()
            coverage_table.columns = ["Check", "Records", "Denominator", "Share"]
            ui.show_table(
                coverage_table,
                column_config={"Share": st.column_config.NumberColumn(format="%.2f%%")},
                height=300,
            )
            geolocation = report["table_counts"].get("olist_geolocation_dataset", 0)
            st.caption(
                f"The geolocation lookup table ({format_int(geolocation)} rows) is retained in the database but "
                "is not used by this dashboard; its profiling is intentionally excluded."
            )

    with miss_tab:
        ui.section(
            "Missing values by column",
            "Only columns with at least one missing or sentinel value are shown.",
        )
        if missing.empty:
            ui.callout("No missing values detected.", tone="success", icon="✓")
        else:
            display = missing.copy()
            display.columns = ["Table", "Column", "Missing", "Missing %"]
            ui.show_table(
                display,
                column_config={"Missing %": st.column_config.NumberColumn(format="%.2f%%")},
                height=460,
            )
            ui.download_csv(display, "olist_missing_values.csv", "Download missing-value report")

    with dates_tab:
        ui.section(
            "Date validation",
            "Counts exclude missing timestamps from the denominator of impossible-sequence checks.",
        )
        date_display = invalid_dates.copy()
        date_display.columns = ["Table", "Check", "Records", "Share"]
        ui.show_table(
            date_display,
            column_config={"Share": st.column_config.NumberColumn(format="%.2f%%")},
            height=430,
        )
        ui.download_csv(date_display, "olist_invalid_dates.csv", "Download date checks")

        date_chart = invalid_dates[invalid_dates["records"] > 0].sort_values("records", ascending=True)
        if date_chart.empty:
            ui.callout("No invalid date sequences detected.", tone="success", icon="✓")
        else:
            ui.section("Invalid date records", "Checks with one or more flagged records.")
            ui.plot(
                charts.horizontal_bar(
                    date_chart,
                    "check",
                    "records",
                    "Records",
                    height=max(300, len(date_chart) * 27),
                    kind="number",
                    color=COLORS["red"],
                ),
                height=max(300, len(date_chart) * 27),
            )

    with integrity_tab:
        left, right = st.columns([1.05, 1], gap="large")
        with left:
            ui.section(
                "Referential integrity",
                "Foreign-key relationships between the source tables.",
            )
            integrity_display = integrity.copy()
            integrity_display.columns = ["Relationship", "Child key", "Parent key", "Orphans", "Severity"]
            ui.show_table(integrity_display, height=330)
        with right:
            ui.section(
                "Duplicate keys",
                "Critical duplicates break entity uniqueness. Expected duplicates are informational.",
            )
            duplicate_display = duplicates.copy()
            duplicate_display.columns = ["Table", "Key", "Duplicate rows", "Severity"]
            ui.show_table(duplicate_display, height=330)

        ui.section(
            "Interpretation",
            "How to read the duplicate and integrity findings.",
        )
        review_dupes = duplicates.loc[duplicates["key"].eq("review_id"), "duplicate_rows"].sum()
        multi_reviews = duplicates.loc[
            duplicates["key"].eq("order_id (multiple reviews)"), "duplicate_rows"
        ].sum()
        customer_dupes = duplicates.loc[
            duplicates["key"].eq("customer_unique_id"), "duplicate_rows"
        ].sum()
        ui.callout(
            f"{format_int(review_dupes)} duplicate review_id values and {format_int(multi_reviews)} orders with "
            f"multiple review rows are expected in the raw source. The dashboard keeps the latest review per order. "
            f"{format_int(customer_dupes)} repeated customer_unique_id values are also expected: customer_id is the "
            "order-level identity, while customer_unique_id identifies the person across orders.",
            tone="info",
            icon="i",
        )
        ui.callout(
            "A product-category translation warning is expected for categories with no English mapping. "
            "The dashboard converts those names to a human-readable fallback rather than dropping them.",
            tone="warning",
            icon="!",
        )

    ui.footer_note(ctx.source_path)
