"""Plotly chart builders with a consistent visual language."""
from __future__ import annotations

from typing import Iterable, Sequence

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .config import COLORS, PALETTE
from .theme import chart_tokens

FONT = "Inter, Segoe UI, Helvetica Neue, Arial, sans-serif"


def _style(
    fig: go.Figure,
    height: int = 360,
    showlegend: bool = False,
    margin: dict | None = None,
    hovermode: str = "x unified",
) -> go.Figure:
    t = chart_tokens()
    fig.update_layout(
        template=t["chart_template"],
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, size=11, color=t["chart_text"]),
        margin=margin or dict(l=10, r=10, t=20, b=10),
        hoverlabel=dict(
            bgcolor=t["chart_hover"],
            bordercolor=t["chart_hover_border"],
            font=dict(family=FONT, size=11, color=t["chart_hover_text"]),
        ),
        colorway=t["chart_palette"],
        showlegend=showlegend,
        hovermode=hovermode,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=10, color=t["chart_muted"]),
            bgcolor="rgba(0,0,0,0)",
        ),
        separators=".,",
    )
    fig.update_xaxes(
        showgrid=False,
        linecolor=t["chart_axis"],
        tickfont=dict(size=10, color=t["chart_muted"]),
        title_font=dict(size=10, color=t["chart_faint"]),
    )
    fig.update_yaxes(
        gridcolor=t["chart_grid"],
        zeroline=False,
        linecolor=t["chart_axis"],
        tickfont=dict(size=10, color=t["chart_muted"]),
        title_font=dict(size=10, color=t["chart_faint"]),
    )
    return fig


def _axis_format(axis: str = "y", kind: str = "number") -> dict:
    if kind == "currency":
        return {"tickprefix": "R$ ", "tickformat": "~s"}
    if kind == "percent":
        return {"ticksuffix": "%", "tickformat": ".0f"}
    if kind == "days":
        return {"ticksuffix": "d", "tickformat": ".0f"}
    if kind == "score":
        return {"range": [0, 5.4], "tickformat": ".1f"}
    return {"tickformat": ","}


def revenue_orders_trend(monthly: pd.DataFrame, height: int = 360) -> go.Figure:
    t = chart_tokens()
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(
            x=monthly["purchase_month"],
            y=monthly["total_orders"],
            name="Orders",
            marker_color=t["chart_bar_soft"],
            hovertemplate="%{x|%b %Y}<br>Orders: %{y:,.0f}<extra></extra>",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=monthly["purchase_month"],
            y=monthly["revenue"],
            name="Product revenue",
            mode="lines+markers",
            line=dict(color=t["blue"], width=2.6),
            marker=dict(size=5, color=t["blue"]),
            hovertemplate="%{x|%b %Y}<br>Revenue: R$ %{y:,.0f}<extra></extra>",
        ),
        secondary_y=True,
    )
    fig.update_yaxes(title_text="Orders", secondary_y=False, showgrid=True, **_axis_format("y", "number"))
    fig.update_yaxes(
        title_text="Product revenue",
        secondary_y=True,
        showgrid=False,
        **_axis_format("y", "currency"),
    )
    fig.update_xaxes(tickformat="%b %y", dtick="M2")
    _style(fig, height=height, showlegend=True)
    return fig


def dual_metric_trend(
    frame: pd.DataFrame,
    x: str,
    bar: str,
    line: str,
    bar_name: str,
    line_name: str,
    bar_kind: str = "number",
    line_kind: str = "percent",
    height: int = 360,
) -> go.Figure:
    t = chart_tokens()
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(
            x=frame[x],
            y=frame[bar],
            name=bar_name,
            marker_color=t["chart_blue_soft"],
            hovertemplate=f"%{{x|%b %Y}}<br>{bar_name}: %{{y:,.1f}}<extra></extra>",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=frame[x],
            y=frame[line],
            name=line_name,
            mode="lines+markers",
            line=dict(color=t["brand"], width=2.6),
            marker=dict(size=5, color=t["brand"]),
            hovertemplate=f"%{{x|%b %Y}}<br>{line_name}: %{{y:,.1f}}<extra></extra>",
        ),
        secondary_y=True,
    )
    fig.update_yaxes(title_text=bar_name, secondary_y=False, **_axis_format("y", bar_kind))
    fig.update_yaxes(title_text=line_name, secondary_y=True, showgrid=False, **_axis_format("y", line_kind))
    fig.update_xaxes(tickformat="%b %y", dtick="M2")
    _style(fig, height=height, showlegend=True)
    return fig


def horizontal_bar(
    frame: pd.DataFrame,
    category: str,
    value: str,
    value_name: str,
    height: int | None = None,
    kind: str = "currency",
    top_n: int | None = None,
    color: str | None = None,
    text_format: str | None = None,
    label_column: str | None = None,
) -> go.Figure:
    t = chart_tokens()
    data = frame.dropna(subset=[value]).sort_values(value).copy()
    if top_n:
        data = data.tail(top_n)
    label_column = label_column or category
    if kind == "currency":
        text = data[value].map(lambda value: f"R$ {value / 1_000_000:,.1f}M" if abs(value) >= 1_000_000 else f"R$ {value / 1_000:,.0f}K")
    elif kind == "percent":
        text = data[value].map(lambda value: f"{value:,.1f}%")
    elif kind == "days":
        text = data[value].map(lambda value: f"{value:,.1f}d")
    elif kind == "score":
        text = data[value].map(lambda value: f"{value:,.2f}★")
    else:
        text = data[value].map(lambda value: f"{value:,.0f}")
    if text_format:
        text = data[value].map(lambda value: text_format.format(value))

    fig = go.Figure(
        go.Bar(
            x=data[value],
            y=data[label_column],
            orientation="h",
            marker=dict(
                color=color or t["brand"],
                line=dict(width=0),
            ),
            text=text,
            textposition="outside",
            cliponaxis=False,
            textfont=dict(size=10, color=t["chart_text"]),
            hovertemplate=(
                f"%{{y}}<br>{value_name}: "
                + ("R$ %{x:,.2f}" if kind == "currency" else "%{x:,.2f}")
                + "<extra></extra>"
            ),
        )
    )
    chart_height = height or max(300, 26 * len(data) + 50)
    _style(
        fig,
        height=chart_height,
        margin=dict(l=8, r=65, t=12, b=8),
        hovermode="closest",
    )
    fig.update_xaxes(showgrid=True, gridcolor=t["chart_grid"], **_axis_format("x", kind))
    fig.update_yaxes(showgrid=False, autorange=True)
    return fig


def vertical_bar(
    frame: pd.DataFrame,
    x: str,
    y: str,
    value_name: str,
    kind: str = "number",
    color: str | Sequence[str] | None = None,
    height: int = 340,
    text_suffix: str = "",
    category_order: Sequence[str] | None = None,
) -> go.Figure:
    t = chart_tokens()
    text = frame[y].map(lambda value: f"{value:,.1f}{text_suffix}" if isinstance(value, float) else f"{value:,.0f}{text_suffix}")
    fig = go.Figure(
        go.Bar(
            x=frame[x],
            y=frame[y],
            marker=dict(color=color or t["brand"], line=dict(width=0)),
            text=text,
            textposition="outside",
            cliponaxis=False,
            textfont=dict(size=10, color=t["chart_text"]),
            hovertemplate=(
                f"%{{x}}<br>{value_name}: "
                + ("R$ %{y:,.2f}" if kind == "currency" else "%{y:,.2f}")
                + "<extra></extra>"
            ),
        )
    )
    if category_order:
        fig.update_xaxes(categoryorder="array", categoryarray=list(category_order))
    _style(fig, height=height, margin=dict(l=8, r=8, t=18, b=10), hovermode="closest")
    fig.update_yaxes(**_axis_format("y", kind))
    fig.update_xaxes(showgrid=False)
    return fig


def donut(
    labels: Sequence,
    values: Sequence,
    center_text: str | None = None,
    height: int = 330,
    colors: Sequence[str] | None = None,
    show_percent: bool = True,
) -> go.Figure:
    t = chart_tokens()
    slice_text = "#0B0B12" if t["mode"] == "dark" else "#FFFFFF"
    fig = go.Figure(
        go.Pie(
            labels=list(labels),
            values=list(values),
            hole=0.62,
            sort=False,
            marker=dict(
                colors=list(colors) if colors else list(PALETTE),
                line=dict(color=t["chart_surface"], width=2),
            ),
            textinfo="percent" if show_percent and len(labels) <= 6 else "none",
            textposition="inside",
            insidetextorientation="horizontal",
            textfont=dict(size=10, color=slice_text),
            hovertemplate="%{label}<br>%{value:,.0f} (%{percent})<extra></extra>",
        )
    )
    if center_text:
        fig.add_annotation(
            text=center_text,
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=15, color=t["chart_ink"], family=FONT),
        )
    _style(fig, height=height, showlegend=True, margin=dict(l=4, r=4, t=8, b=4), hovermode="closest")
    fig.update_layout(
        legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.02, font=dict(size=10)),
        margin=dict(l=4, r=90, t=8, b=4),
    )
    return fig


def line_chart(
    frame: pd.DataFrame,
    x: str,
    y: str,
    value_name: str,
    kind: str = "number",
    color: str | None = None,
    height: int = 340,
    fill: bool = False,
) -> go.Figure:
    t = chart_tokens()
    fig = go.Figure(
        go.Scatter(
            x=frame[x],
            y=frame[y],
            mode="lines+markers",
            line=dict(color=color or COLORS["teal"], width=2.6),
            marker=dict(size=4),
            fill="tozeroy" if fill else None,
            fillcolor=t["chart_fill"] if fill else None,
            name=value_name,
            hovertemplate=f"%{{x|%b %Y}}<br>{value_name}: "
            + ("R$ %{y:,.2f}" if kind == "currency" else "%{y:,.2f}")
            + "<extra></extra>",
        )
    )
    _style(fig, height=height, hovermode="x unified")
    fig.update_xaxes(tickformat="%b %y", dtick="M2")
    fig.update_yaxes(**_axis_format("y", kind))
    return fig


def histogram(
    values: pd.Series,
    value_name: str,
    color: str | None = None,
    height: int = 340,
    nbins: int = 45,
    kind: str = "number",
    median_line: bool = True,
) -> go.Figure:
    t = chart_tokens()
    series = pd.to_numeric(values, errors="coerce").dropna()
    fig = go.Figure(
        go.Histogram(
            x=series,
            nbinsx=nbins,
            marker=dict(
                color=color or t["chart_bar_soft"],
                line=dict(color=t["chart_surface"], width=0.6),
            ),
            hovertemplate="Range: %{x}<br>Orders: %{y:,.0f}<extra></extra>",
            name=value_name,
        )
    )
    if median_line and len(series):
        median = float(series.median())
        fig.add_vline(
            x=median,
            line=dict(color=COLORS["amber"], width=2, dash="dash"),
            annotation_text=f"Median {median:,.1f}",
            annotation_position="top right",
            annotation_font=dict(size=10, color=COLORS["amber"]),
        )
    _style(fig, height=height, margin=dict(l=8, r=8, t=24, b=8), hovermode="closest")
    fig.update_xaxes(title_text=value_name, **_axis_format("x", kind))
    fig.update_yaxes(title_text="Orders", **_axis_format("y", "number"))
    return fig


def stacked_area(
    frame: pd.DataFrame,
    x: str,
    columns: Sequence[str],
    labels: Sequence[str] | None = None,
    height: int = 380,
) -> go.Figure:
    labels = labels or columns
    fig = go.Figure()
    for index, (column, label) in enumerate(zip(columns, labels)):
        fig.add_trace(
            go.Scatter(
                x=frame[x],
                y=frame[column],
                name=str(label),
                mode="lines",
                stackgroup="one",
                line=dict(width=0.6, color=PALETTE[index % len(PALETTE)]),
                fillcolor=PALETTE[index % len(PALETTE)],
                hovertemplate=f"%{{x|%b %Y}}<br>{label}: %{{y:,.0f}}<extra></extra>",
            )
        )
    _style(fig, height=height, showlegend=True, hovermode="x unified")
    fig.update_xaxes(tickformat="%b %y", dtick="M3")
    fig.update_yaxes(tickprefix="R$ ", tickformat="~s")
    return fig


def stacked_bar(
    frame: pd.DataFrame,
    x: str,
    columns: Sequence[str],
    labels: Sequence[str] | None = None,
    height: int = 360,
    kind: str = "number",
) -> go.Figure:
    labels = labels or columns
    fig = go.Figure()
    for index, (column, label) in enumerate(zip(columns, labels)):
        fig.add_trace(
            go.Bar(
                x=frame[x],
                y=frame[column],
                name=str(label),
                marker_color=PALETTE[index % len(PALETTE)],
                hovertemplate=f"%{{x|%b %Y}}<br>{label}: %{{y:,.0f}}<extra></extra>",
            )
        )
    _style(fig, height=height, showlegend=True, hovermode="x unified")
    fig.update_layout(barmode="stack")
    fig.update_xaxes(tickformat="%b %y", dtick="M3")
    fig.update_yaxes(**_axis_format("y", kind))
    return fig



def treemap(frame: pd.DataFrame, path: str, value: str, height: int = 420) -> go.Figure:
    t = chart_tokens()
    data = frame.dropna(subset=[value]).copy()
    fig = px.treemap(
        data,
        path=[px.Constant("All categories"), path],
        values=value,
        color=value,
        color_continuous_scale=t["chart_scale"],
        custom_data=[value],
    )
    fig.update_traces(
        textinfo="label+value",
        texttemplate="<b>%{label}</b><br>R$ %{value:,.0f}",
        hovertemplate="%{label}<br>Revenue: R$ %{value:,.0f}<extra></extra>",
        marker=dict(line=dict(width=1.5, color=t["chart_surface"])),
        textfont=dict(size=11, family=FONT),
    )
    fig.update_layout(
        coloraxis_showscale=False,
        margin=dict(l=4, r=4, t=6, b=4),
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, size=11, color=t["chart_text"]),
    )
    return fig


def pareto_chart(
    frame: pd.DataFrame,
    label: str,
    value: str,
    height: int = 360,
    top_n: int = 200,
) -> go.Figure:
    t = chart_tokens()
    data = frame.sort_values(value, ascending=False).head(top_n).copy()
    data["cumulative_share"] = data[value].cumsum() / data[value].sum() * 100
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(
            x=np.arange(1, len(data) + 1),
            y=data[value],
            name="Revenue",
            marker_color=t["chart_bar_soft"],
            hovertemplate="Rank %{x}<br>Revenue: R$ %{y:,.0f}<extra></extra>",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=np.arange(1, len(data) + 1),
            y=data["cumulative_share"],
            name="Cumulative share",
            mode="lines",
            line=dict(color=COLORS["amber"], width=2.4),
            hovertemplate="Rank %{x}<br>Cumulative: %{y:,.1f}%<extra></extra>",
        ),
        secondary_y=True,
    )
    _style(fig, height=height, showlegend=True, hovermode="x")
    fig.update_xaxes(title_text=f"{label} rank")
    fig.update_yaxes(title_text="Revenue", secondary_y=False, tickprefix="R$ ", tickformat="~s")
    fig.update_yaxes(title_text="Cumulative share", secondary_y=True, ticksuffix="%", range=[0, 105], showgrid=False)
    return fig


def review_distribution(frame: pd.DataFrame, height: int = 330) -> go.Figure:
    t = chart_tokens()
    data = frame.copy()
    data["label"] = data["review_score"].map(lambda score: f"{int(score)}★")
    colors = t["score_colors"]
    fig = go.Figure(
        go.Bar(
            x=data["label"],
            y=data["reviews"],
            marker=dict(color=colors[: len(data)], line=dict(width=0)),
            text=data["share"].map(lambda value: f"{value:,.1f}%"),
            textposition="outside",
            cliponaxis=False,
            textfont=dict(size=10, color=t["chart_text"]),
            hovertemplate="%{x}<br>Reviews: %{y:,.0f}<extra></extra>",
        )
    )
    _style(fig, height=height, margin=dict(l=8, r=8, t=18, b=8), hovermode="closest")
    fig.update_yaxes(title_text="Reviews", tickformat=",")
    fig.update_xaxes(title_text="Review score")
    return fig


def delay_score_bars(frame: pd.DataFrame, height: int = 360) -> go.Figure:
    t = chart_tokens()
    data = frame.dropna(subset=["avg_score"]).copy()
    colors = []
    for score in data["avg_score"]:
        if score >= 4.2:
            colors.append(COLORS["green"])
        elif score >= 3.5:
            colors.append(COLORS["amber"])
        else:
            colors.append(COLORS["red"])
    fig = go.Figure(
        go.Bar(
            x=data["delay_bucket"],
            y=data["avg_score"],
            marker=dict(color=colors, line=dict(width=0)),
            text=[
                f"{score:,.2f} ★<br>{count:,.0f} reviews"
                for score, count in zip(data["avg_score"], data["reviews"])
            ],
            textposition="outside",
            cliponaxis=False,
            textfont=dict(size=10, color=t["chart_text"]),
            hovertemplate="%{x}<br>Average score: %{y:.2f}<extra></extra>",
        )
    )
    _style(fig, height=height, margin=dict(l=8, r=8, t=28, b=10), hovermode="closest")
    fig.update_yaxes(title_text="Average review score", range=[0, 5.6], tickformat=".1f")
    fig.update_xaxes(title_text="Delivery versus estimate")
    return fig


def installments_chart(frame: pd.DataFrame, height: int = 350) -> go.Figure:
    t = chart_tokens()
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(
            x=frame["installments"],
            y=frame["orders"],
            name="Orders",
            marker_color=t["chart_blue_soft"],
            hovertemplate="%{x} installments<br>Orders: %{y:,.0f}<extra></extra>",
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=frame["installments"],
            y=frame["avg_value"],
            name="Average order value",
            mode="lines+markers",
            line=dict(color=COLORS["amber"], width=2.2),
            marker=dict(size=4),
            hovertemplate="%{x} installments<br>Avg value: R$ %{y:,.2f}<extra></extra>",
        ),
        secondary_y=True,
    )
    _style(fig, height=height, showlegend=True, hovermode="x unified")
    fig.update_xaxes(title_text="Installments", dtick=1)
    fig.update_yaxes(title_text="Orders", secondary_y=False, tickformat=",")
    fig.update_yaxes(title_text="Avg order value", secondary_y=True, tickprefix="R$ ", tickformat="~s", showgrid=False)
    return fig


def scatter(
    frame: pd.DataFrame,
    x: str,
    y: str,
    x_name: str,
    y_name: str,
    color: str | None = None,
    size: str | None = None,
    height: int = 360,
    hover_name: str | None = None,
    kind_x: str = "number",
    kind_y: str = "number",
) -> go.Figure:
    t = chart_tokens()
    fig = px.scatter(
        frame,
        x=x,
        y=y,
        color=color,
        size=size,
        hover_name=hover_name,
        color_discrete_sequence=list(PALETTE),
        opacity=0.75,
    )
    fig.update_traces(marker=dict(line=dict(width=0.5, color=t["chart_surface"])))
    _style(fig, height=height, showlegend=bool(color), hovermode="closest")
    fig.update_xaxes(title_text=x_name, **_axis_format("x", kind_x))
    fig.update_yaxes(title_text=y_name, **_axis_format("y", kind_y))
    return fig
