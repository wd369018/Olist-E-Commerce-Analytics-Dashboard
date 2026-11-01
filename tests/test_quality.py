"""Data quality report tests."""
from __future__ import annotations

from dashboard.quality import quality_report


def test_quality_summary_is_non_negative(data):
    summary = quality_report(data)["summary"]
    for key, value in summary.items():
        assert value >= 0, key
    assert summary["tables_profiled"] == 8
    assert summary["rows_profiled"] == 550_759
    assert summary["duplicate_rows"] == 0
    assert summary["duplicate_key_issues"] == 0


def test_referential_integrity_has_no_critical_orphans(data):
    report = quality_report(data)
    integrity = report["integrity"]
    assert (integrity["orphans"] >= 0).all()
    critical = integrity[integrity["severity"] == "critical"]
    assert critical["orphans"].sum() == 0
    assert report["summary"]["orphan_records"] == 13
    translation = integrity[
        integrity["relationship"].eq("Product categories → translation")
    ]
    assert translation["orphans"].iloc[0] == 13


def test_duplicate_keys_are_classified(data):
    duplicates = quality_report(data)["duplicates"]
    critical = duplicates[duplicates["severity"] == "critical"]
    assert critical["duplicate_rows"].sum() == 0
    expected = duplicates[duplicates["severity"] == "expected"]
    assert expected["duplicate_rows"].sum() == 3_345
    reviews = duplicates[duplicates["table"].eq("Reviews")]
    assert reviews["duplicate_rows"].sum() > 0


def test_invalid_date_checks(data):
    invalid = quality_report(data)["invalid_dates"]
    counts = invalid.set_index("check")["records"]
    assert counts["Approved before purchase"] == 0
    assert counts["Delivered before purchase"] == 0
    assert counts["Estimated delivery before purchase"] == 0
    assert counts["Carrier handoff before purchase"] == 166
    assert counts["Delivered before carrier handoff"] == 23
    assert counts["Delivered status without delivery date"] == 8
    assert counts["Review created before purchase"] == 74
    assert counts["Delivery time over 365 days"] == 0
    assert invalid["records"].ge(0).all()
    assert invalid["pct"].between(0, 100).all()


def test_coverage_checks(data):
    coverage = quality_report(data)["coverage"].set_index("check")
    assert coverage.loc["Orders without items", "records"] == 775
    assert coverage.loc["Orders without payments", "records"] == 1
    assert coverage.loc["Orders without reviews", "records"] == 768
    assert coverage.loc["Customers without orders", "records"] == 0
    assert coverage["records"].sum() == 1_544


def test_missing_value_profile(data):
    report = quality_report(data)
    profiles = report["profiles"].set_index("table")
    assert profiles.loc["Orders", "rows"] == 99_441
    assert profiles.loc["Reviews (raw)", "rows"] == 99_224
    assert report["summary"]["missing_cells"] == 164_370

    missing = report["missing"].set_index(["table", "column"])["missing"]
    assert missing.loc[("Reviews (raw)", "review_comment_message")] == 58_276
    assert missing.loc[("Reviews (raw)", "review_comment_title")] == 87_671
    assert missing.loc[("Products", "product_category_name")] == 610
    assert missing.loc[("Order items", "product_category_name")] == 1_603


def test_quality_tables_are_download_ready(data):
    report = quality_report(data)
    expected = {
        "profiles",
        "missing",
        "invalid_dates",
        "integrity",
        "duplicates",
        "coverage",
        "summary",
        "table_counts",
    }
    assert expected == set(report)
    for key in expected - {"summary", "table_counts"}:
        assert not report[key].empty
