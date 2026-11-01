"""Streamlit smoke tests for the app shell and every page."""
from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import Mock

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app.py"
PAGES = ROOT / "dashboard" / "pages"


@pytest.fixture(scope="module")
def app():
    at = AppTest.from_file(str(APP), default_timeout=900)
    at.run()
    return at


def test_app_shell_renders_without_exceptions(app):
    assert not app.exception
    assert len(app.sidebar.multiselect) == 3
    assert [button.label for button in app.button] == ["Reset", "Reload"]
    assert len(app.get("plotly_chart")) >= 4
    assert len(app.markdown) > 0


def test_app_renders_dark_theme_and_single_day_selection():
    at = AppTest.from_file(str(APP), default_timeout=900)
    at.session_state["theme_mode"] = "dark"
    at.session_state["filter_date_range"] = (date(2018, 1, 1),)
    at.run()
    assert not at.exception
    combined = " ".join(block.value for block in at.markdown)
    assert "#08080D" in combined  # dark canvas token is active
    assert at.session_state["filter_date_range"] == (date(2018, 1, 1),)


def test_app_filter_updates_dashboard(app):
    app.session_state["filter_statuses"] = ["canceled"]
    app.run()
    assert not app.exception
    combined = " ".join(block.value for block in app.markdown)
    assert "625" in combined
    # The canceled-only selection contains no delivered orders.
    assert "0 delivered" in combined or "0.0% delivery rate" in combined

    app.session_state["filter_statuses"] = []
    app.run()
    assert not app.exception


def test_kpi_cards_allow_html(monkeypatch):
    from dashboard import ui

    markdown = Mock()
    monkeypatch.setattr(ui.st, "markdown", markdown)
    ui.kpi_cards([{"label": "Orders", "value": "100"}])
    assert markdown.call_args.kwargs == {"unsafe_allow_html": True}


@pytest.mark.parametrize("mode", ["light", "dark"])
@pytest.mark.parametrize(
    "page",
    [
        "executive.py",
        "sales.py",
        "customers.py",
        "products.py",
        "delivery.py",
        "satisfaction.py",
        "payments.py",
        "data_quality.py",
    ],
)
def test_every_page_renders_without_exceptions(page, mode):
    at = AppTest.from_file(str(PAGES / page), default_timeout=900)
    at.session_state["theme_mode"] = mode
    at.run()
    assert not at.exception, f"{page} ({mode}) raised: {[exc.value for exc in at.exception]}"
    assert len(at.get("plotly_chart")) >= 1


@pytest.mark.parametrize(
    "page",
    [
        "executive.py",
        "sales.py",
        "customers.py",
        "products.py",
        "delivery.py",
        "satisfaction.py",
        "payments.py",
    ],
)
def test_pages_render_with_empty_date_range(page):
    """A period with no orders must show empty states instead of raising."""
    at = AppTest.from_file(str(PAGES / page), default_timeout=900)
    at.session_state["filter_date_range"] = (date(2016, 1, 1), date(2016, 1, 31))
    at.run()
    assert not at.exception, f"{page} raised: {[exc.value for exc in at.exception]}"


@pytest.mark.parametrize(
    "page",
    [
        "executive.py",
        "sales.py",
        "customers.py",
        "products.py",
        "delivery.py",
        "satisfaction.py",
        "payments.py",
    ],
)
def test_pages_render_with_only_canceled_orders(page):
    """Canceled-only filters leave no delivered orders or item revenue on several pages."""
    at = AppTest.from_file(str(PAGES / page), default_timeout=900)
    at.session_state["filter_statuses"] = ["canceled"]
    at.run()
    assert not at.exception, f"{page} raised: {[exc.value for exc in at.exception]}"
