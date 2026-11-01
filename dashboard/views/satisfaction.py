"""Customer satisfaction page."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from .. import charts, metrics, ui
from ..config import COLORS, METRIC_HELP
from ..filters import AnalysisContext
from ..formatting import format_int, format_number, format_pct


def render(ctx: AnalysisContext) -> None:
    satisfaction = metrics.satisfaction_metrics(ctx)
    category_scores = metrics.category_reviews(ctx, min_reviews=30)

    ui.page_header(
        "Customer satisfaction",
        "Review scores, category-level sentiment and the measurable relationship between delivery delays and ratings.",
        eyebrow="Voice of the customer",
    )
    ui.active_filter_bar(ctx)

    cards = [
        {
            "label": "Average review score",
            "value": f"{format_number(satisfaction['avg_score'], 2)} / 5",
            "sub": f"{format_int(satisfaction['review_count'])} reviewed orders",
            "accent": COLORS["amber"],
            "help": METRIC_HELP["review_score"],
        },
        {
            "label": "Five-star rate",
            "value": format_pct(satisfaction["five_star_rate"]),
            "sub": "Share of reviewed orders",
            "accent": COLORS["green"],
        },
        {
            "label": "Low-score rate",
            "value": format_pct(satisfaction["low_score_rate"]),
            "sub": "Scores of 1 or 2",
            "accent": COLORS["red"],
        },
        {
            "label": "Review coverage",
            "value": format_pct(satisfaction["review_coverage"]),
            "sub": "Orders with at least one review",
            "accent": COLORS["blue"],
        },
        {
            "label": "On-time avg score",
            "value": format_number(satisfaction["on_time_avg_score"], 2),
            "sub": f"{format_int(satisfaction['on_time_reviews'])} reviews",
            "accent": COLORS["teal"],
        },
        {
            "label": "Late avg score",
            "value": format_number(satisfaction["late_avg_score"], 2),
            "sub": f"{format_int(satisfaction['late_reviews'])} reviews",
            "accent": COLORS["red"],
        },
    ]
    ui.kpi_cards(cards)

    if satisfaction["review_count"] == 0:
        ui.empty_state("No reviews in this selection", "Widen the filters to analyse customer satisfaction.")
        ui.footer_note(ctx.source_path)
        return

    left, right = st.columns([1, 1.2], gap="large")
    with left:
        ui.section("Review score distribution", "Latest review per order.")
        ui.plot(charts.review_distribution(satisfaction["distribution"], height=360), height=360)
    with right:
        ui.section("Satisfaction trend", "Average review score by purchase month.")
        ui.plot(
            charts.line_chart(
                satisfaction["monthly"],
                "purchase_month",
                "avg_score",
                "Average review score",
                kind="score",
                color=COLORS["amber"],
                height=360,
                fill=True,
            ),
            height=360,
        )

    ui.section(
        "Delivery delays versus ratings",
        "Delivered orders with valid dates and a review. The first bucket includes early and on-time deliveries.",
    )
    buckets = satisfaction["delay_buckets"]
    if buckets.empty:
        ui.empty_state(
            "No delivery-linked reviews",
            "No reviewed order in this selection has usable delivery and estimated dates.",
        )
    else:
        left, right = st.columns([1.2, 1], gap="large")
        with left:
            ui.plot(charts.delay_score_bars(buckets, height=370), height=370)
        with right:
            if pd.notna(satisfaction["score_gap"]):
                ui.callout(
                    f"On-time or early orders average {satisfaction['on_time_avg_score']:.2f} stars, versus "
                    f"{satisfaction['late_avg_score']:.2f} for late orders — a "
                    f"{satisfaction['score_gap']:.2f}-point gap.",
                    tone="danger" if satisfaction["score_gap"] > 0.3 else "warning",
                    icon="!",
                )
            if pd.notna(satisfaction["correlation"]):
                direction = "negative" if satisfaction["correlation"] < 0 else "positive"
                strength = (
                    "strong"
                    if abs(satisfaction["correlation"]) >= 0.5
                    else "moderate"
                    if abs(satisfaction["correlation"]) >= 0.3
                    else "weak"
                )
                ui.callout(
                    f"Spearman rank correlation between delay days and review score is "
                    f"{satisfaction['correlation']:.3f}: a {strength} {direction} relationship. "
                    "Correlation is descriptive, not causal.",
                    tone="info",
                    icon="i",
                )

    left, right = st.columns([1, 1], gap="large")
    with left:
        ui.section("Highest-rated categories", "Categories with at least 30 reviews.")
        if category_scores.empty:
            ui.empty_state("Not enough category reviews", "No category has 30+ reviews in this selection.")
        else:
            best = category_scores.head(12).copy()
            best["display"] = best["category"].str.replace("_", " ").str.title()
            best = best.sort_values("avg_score", ascending=True)
            ui.plot(
                charts.horizontal_bar(
                    best,
                    "display",
                    "avg_score",
                    "Average score",
                    height=430,
                    kind="score",
                    color=COLORS["green"],
                ),
                height=430,
            )
    with right:
        ui.section("Lowest-rated categories", "Largest opportunities to improve the customer experience.")
        if category_scores.empty:
            ui.empty_state("Not enough category reviews", "No category has 30+ reviews in this selection.")
        else:
            worst = category_scores.sort_values("avg_score").head(12).copy()
            worst["display"] = worst["category"].str.replace("_", " ").str.title()
            worst = worst.sort_values("avg_score", ascending=True)
            ui.plot(
                charts.horizontal_bar(
                    worst,
                    "display",
                    "avg_score",
                    "Average score",
                    height=430,
                    kind="score",
                    color=COLORS["red"],
                ),
                height=430,
            )

    ui.section("Category rating table", "Review scores and low-score incidence by category (30+ reviews).")
    if category_scores.empty:
        ui.empty_state("Not enough category reviews", "No category has 30+ reviews in this selection.")
    else:
        table = category_scores.copy()
        table["category"] = table["category"].str.replace("_", " ").str.title()
        table = table[["category", "reviews", "avg_score", "five_star_rate", "low_score_rate"]]
        table.columns = ["Category", "Reviews", "Avg score", "Five-star rate", "Low-score rate"]
        ui.show_table(
            table,
            column_config={
                "Avg score": st.column_config.NumberColumn(format="%.2f"),
                "Five-star rate": st.column_config.NumberColumn(format="%.1f%%"),
                "Low-score rate": st.column_config.NumberColumn(format="%.1f%%"),
            },
            height=430,
        )
        ui.download_csv(table, "olist_category_ratings.csv", "Download category ratings")

    ui.callout(
        "Reviews are deduplicated to the latest review per order. Category ratings attribute an order's review "
        "to every category present in that order, so category review counts are not additive.",
        tone="info",
        icon="i",
    )
    ui.footer_note(ctx.source_path)
