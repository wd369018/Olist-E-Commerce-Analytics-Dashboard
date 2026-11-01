"""Streamlit-aware cached data access and filter session state."""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from .filters import AnalysisContext, FilterSelection, apply_filters, filter_options
from .quality import quality_report
from utils.data_loader import load_dataset, resolve_dataset_path


def database_path() -> str:
    return str(resolve_dataset_path())


def get_data(db_path: str) -> dict[str, Any]:
    return load_dataset(db_path)


@st.cache_data(show_spinner=False, max_entries=2)
def get_filter_options(db_path: str) -> dict[str, Any]:
    return filter_options(get_data(db_path))


@st.cache_data(show_spinner=False, max_entries=2)
def get_quality_report(db_path: str) -> dict[str, Any]:
    return quality_report(get_data(db_path))


@st.cache_data(show_spinner=False, max_entries=4)
def _filtered_context(
    db_path: str,
    start: str | None,
    end: str | None,
    statuses: tuple[str, ...],
    states: tuple[str, ...],
    categories: tuple[str, ...],
) -> AnalysisContext:
    data = get_data(db_path)
    selection = FilterSelection(
        start_date=date.fromisoformat(start) if start else None,
        end_date=date.fromisoformat(end) if end else None,
        statuses=statuses,
        states=states,
        categories=categories,
    )
    return apply_filters(data, selection)


def _as_date(value: Any) -> date | None:
    """Coerce a widget value to a timezone-free calendar date."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        val = value.strip()
        if not val:
            return None
        # Try ISO format (YYYY-MM-DD)
        try:
            return date.fromisoformat(val[:10])
        except ValueError:
            pass
        # Try DD/MM/YYYY or DD-MM-YYYY (matching the widget display format)
        try:
            parsed = pd.to_datetime(val, dayfirst=True, errors="coerce")
            if pd.notna(parsed):
                return parsed.date()
        except Exception:
            pass
        return None
    try:
        parsed = pd.to_datetime(value, errors="coerce")
        if pd.notna(parsed):
            return parsed.date()
    except Exception:
        pass
    return None


def _normalise_date_range(value: Any, minimum: date, maximum: date) -> tuple[date, date]:
    """Normalise partial calendar selections without resetting the user's choice."""
    if isinstance(value, (tuple, list)):
        if len(value) >= 2:
            start, end = _as_date(value[0]), _as_date(value[1])
        elif len(value) == 1:
            start = end = _as_date(value[0])
        else:
            start = end = None
    else:
        start = end = _as_date(value)

    start = start or minimum
    end = end or maximum
    if start > end:
        start, end = end, start
    # Clamp to the available source range so stale session values cannot break pages.
    start = max(min(start, maximum), minimum)
    end = max(min(end, maximum), minimum)
    return start, end


def selection_from_session(options: dict[str, Any]) -> FilterSelection:
    minimum = options["min_date"]
    maximum = options["max_date"]
    start, end = _normalise_date_range(
        st.session_state.get("filter_date_range", (minimum, maximum)), minimum, maximum
    )
    statuses = tuple(st.session_state.get("filter_statuses", ()))
    states = tuple(st.session_state.get("filter_states", ()))
    categories = tuple(st.session_state.get("filter_categories", ()))
    # Guard against stale options after a refresh.
    statuses = tuple(status for status in statuses if status in options["statuses"])
    states = tuple(state for state in states if state in options["states"])
    categories = tuple(category for category in categories if category in options["categories"])
    return FilterSelection(
        start_date=start,
        end_date=end,
        statuses=statuses,
        states=states,
        categories=categories,
    )


def get_context() -> AnalysisContext:
    """Return the filtered analysis context for the current page."""
    db_path = database_path()
    data = get_data(db_path)
    options = filter_options(data)
    selection = selection_from_session(options)
    return _filtered_context(
        db_path,
        selection.start_date.isoformat() if selection.start_date else None,
        selection.end_date.isoformat() if selection.end_date else None,
        selection.statuses,
        selection.states,
        selection.categories,
    )


def reset_filters(options: dict[str, Any]) -> None:
    st.session_state["filter_date_range"] = (options["min_date"], options["max_date"])
    st.session_state["filter_statuses"] = []
    st.session_state["filter_states"] = []
    st.session_state["filter_categories"] = []


def clear_data_cache() -> None:
    st.cache_data.clear()


def source_label(data: dict[str, Any]) -> str:
    path = Path(data["metadata"]["db_path"])
    try:
        relative = path.relative_to(Path.cwd())
        return str(relative)
    except ValueError:
        return str(path)


def filter_summary(selection: FilterSelection, options: dict[str, Any]) -> str:
    start = selection.start_date.strftime("%d %b %Y") if selection.start_date else "—"
    end = selection.end_date.strftime("%d %b %Y") if selection.end_date else "—"
    statuses = ", ".join(selection.statuses) if selection.statuses else "All statuses"
    states = ", ".join(selection.states) if selection.states else "All states"
    categories = (
        f"{len(selection.categories)} selected" if selection.categories else "All categories"
    )
    return f"{start} → {end}  ·  {statuses}  ·  {states}  ·  {categories}"


def date_range_text(data: dict[str, Any]) -> str:
    metadata = data["metadata"]
    start = pd.Timestamp(metadata["date_min"]).strftime("%d %b %Y")
    end = pd.Timestamp(metadata["date_max"]).strftime("%d %b %Y")
    return f"{start} → {end}"
