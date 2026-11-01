"""Formatting helpers shared by dashboard pages."""
from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd


def safe_div(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Divide safely, returning ``default`` for missing or zero denominators."""
    try:
        if denominator is None or numerator is None:
            return default
        denominator = float(denominator)
        numerator = float(numerator)
        if denominator == 0 or math.isnan(denominator) or math.isnan(numerator):
            return default
        result = numerator / denominator
        return default if math.isnan(result) or math.isinf(result) else result
    except (TypeError, ValueError):
        return default


def pct(numerator: float, denominator: float, decimals: int = 1) -> float:
    """Return a percentage value (e.g. 12.3 for 12.3%)."""
    return round(safe_div(numerator, denominator) * 100, decimals)


def format_int(value: Any) -> str:
    if value is None or (isinstance(value, float) and (math.isnan(value) or math.isinf(value))):
        return "—"
    return f"{int(round(float(value))):,}"


def format_currency(value: Any, compact: bool = False, decimals: int = 2) -> str:
    """Format BRL values in a readable, consistent way."""
    if value is None or (isinstance(value, float) and (math.isnan(value) or math.isinf(value))):
        return "—"
    value = float(value)
    sign = "-" if value < 0 else ""
    value = abs(value)
    if compact:
        if value >= 1_000_000_000:
            return f"{sign}R$ {value / 1_000_000_000:,.2f}B"
        if value >= 1_000_000:
            return f"{sign}R$ {value / 1_000_000:,.1f}M"
        if value >= 1_000:
            return f"{sign}R$ {value / 1_000:,.1f}K"
    return f"{sign}R$ {value:,.{decimals}f}"


def format_number(value: Any, decimals: int = 1) -> str:
    if value is None or (isinstance(value, float) and (math.isnan(value) or math.isinf(value))):
        return "—"
    return f"{float(value):,.{decimals}f}"


def format_pct(value: Any, decimals: int = 1) -> str:
    if value is None or (isinstance(value, float) and (math.isnan(value) or math.isinf(value))):
        return "—"
    return f"{float(value):,.{decimals}f}%"


def format_days(value: Any, decimals: int = 1) -> str:
    if value is None or (isinstance(value, float) and (math.isnan(value) or math.isinf(value))):
        return "—"
    return f"{float(value):,.{decimals}f} days"


def format_delta(value: float, unit: str = "%", decimals: int = 1) -> str:
    if value is None or (isinstance(value, float) and (math.isnan(value) or math.isinf(value))):
        return "—"
    arrow = "▲" if value > 0 else ("▼" if value < 0 else "•")
    return f"{arrow} {abs(value):,.{decimals}f}{unit}"


def month_label(value: Any) -> str:
    if pd.isna(value):
        return ""
    return pd.Timestamp(value).strftime("%b %Y")


def to_csv_bytes(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(index=False).encode("utf-8-sig")


def clean_number(value: Any, default: float = 0.0) -> float:
    try:
        value = float(value)
        return default if np.isnan(value) or np.isinf(value) else value
    except (TypeError, ValueError):
        return default
