"""Tests for session date normalisation and theme selection helpers."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from dashboard.context import _normalise_date_range
from dashboard.theme import css_variables, native_sync_script, normalise_mode, tokens

MINIMUM = date(2016, 1, 1)
MAXIMUM = date(2018, 10, 17)


def test_single_date_selection_is_not_reset():
    # A one-item tuple is what Streamlit returns while a range is being picked.
    # It must filter to that day rather than snapping back to the full range.
    start, end = _normalise_date_range((date(2018, 1, 1),), MINIMUM, MAXIMUM)
    assert start == end == date(2018, 1, 1)


def test_two_date_selection_handles_reversed_order():
    start, end = _normalise_date_range(
        (date(2018, 5, 1), date(2018, 1, 1)), MINIMUM, MAXIMUM
    )
    assert start == date(2018, 1, 1)
    assert end == date(2018, 5, 1)


def test_date_selection_is_clamped_to_source_range():
    start, end = _normalise_date_range(
        (date(2010, 1, 1), date(2025, 1, 1)), MINIMUM, MAXIMUM
    )
    assert start == MINIMUM
    assert end == MAXIMUM


def test_timezone_aware_datetime_becomes_calendar_date():
    value = datetime(2018, 3, 4, 23, 30, tzinfo=timezone(timedelta(hours=-3)))
    start, end = _normalise_date_range((value,), MINIMUM, MAXIMUM)
    assert start == end == date(2018, 3, 4)


def test_invalid_values_fall_back_to_full_range():
    start, end = _normalise_date_range(("not-a-date",), MINIMUM, MAXIMUM)
    assert start == MINIMUM
    assert end == MAXIMUM


def test_formatted_date_strings_are_parsed():
    # Supports DD/MM/YYYY and DD-MM-YYYY as configured in the datepicker
    start, end = _normalise_date_range(("01/05/2018", "15/05/2018"), MINIMUM, MAXIMUM)
    assert start == date(2018, 5, 1)
    assert end == date(2018, 5, 15)

    start2, end2 = _normalise_date_range(("2018-05-01",), MINIMUM, MAXIMUM)
    assert start2 == end2 == date(2018, 5, 1)


def test_theme_modes_have_distinct_canvas_and_chrome_tokens():
    light, dark = tokens("light"), tokens("dark")
    assert light["mode"] == "light"
    assert dark["mode"] == "dark"
    assert light["canvas"] != dark["canvas"]
    assert light["ink"] != dark["ink"]
    assert "--bg:" in css_variables("light")
    assert "--bg:" in css_variables("dark")
    assert dark["canvas"] in css_variables("dark")


def test_native_theme_sync_writes_streamlit_json_value():
    script = native_sync_script("dark")
    # Streamlit reads stActiveTheme-<path>-v2 with JSON.parse, so the stored
    # value must include quotes (e.g. "Dark"). A bare Dark would crash the read.
    assert "storedLabel" in script
    assert "JSON.stringify(desiredLabel)" in script
    assert '"Dark"' in script
    assert "stActiveTheme-" in script


def test_theme_mode_normalisation_accepts_lists_and_falls_back():
    assert normalise_mode("Dark") == "dark"
    assert normalise_mode(["light"]) == "light"
    assert normalise_mode("sepia") == "light"
    assert normalise_mode(None, default="dark") == "dark"


def test_stylesheet_has_mobile_breakpoints_and_hides_deploy_control():
    from dashboard.ui import _CSS_TEMPLATE

    assert "@media (max-width: 760px)" in _CSS_TEMPLATE
    assert "@media (max-width: 480px)" in _CSS_TEMPLATE
    assert 'button[aria-label="Deploy"]' in _CSS_TEMPLATE
    assert ".st-key-theme_switch" in _CSS_TEMPLATE
