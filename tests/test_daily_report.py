"""Tests for backend/daily_report.py — report formatting and addon gating."""

from unittest.mock import patch

from backend.daily_report import _format_report, generate_and_send_daily_reports


# --- Report formatting (pure) ------------------------------------------------

def test_format_report_with_data():
    issues = [{"id": 1, "title": "Broken pipe", "severity": "high"}]
    visits = [{"id": 1, "title": "HVAC Vendor", "start_time": "09:00"}]
    important = [{"type": "Issue", "id": 1, "title": "Broken pipe"}]

    report = _format_report("Main Office", issues, visits, important, "2024-01-01")

    assert "Main Office" in report
    assert "Broken pipe" in report
    assert "high" in report
    assert "HVAC Vendor" in report
    assert "09:00" in report


def test_format_report_empty():
    report = _format_report("Main Office", [], [], [], "2024-01-01")

    assert "No new issues" in report
    assert "No vendor visits" in report
    assert "No items flagged" in report


# --- Addon gating -------------------------------------------------------------

@patch("backend.daily_report.send_email")
@patch("backend.daily_report.execute_query")
def test_addon_disabled_skips(mock_eq, mock_send):
    mock_eq.return_value = {"rows": [{"daily_reports_addon": False}]}

    result = generate_and_send_daily_reports(instance_id=42)

    assert result == []
    mock_send.assert_not_called()


@patch("backend.daily_report.send_email")
@patch("backend.daily_report.execute_query")
def test_addon_enabled_sends(mock_eq, mock_send):
    mock_send.return_value = {"success": True}
    mock_eq.side_effect = [
        # addon check
        {"rows": [{"daily_reports_addon": True}]},
        # _get_supervisors
        {"rows": [{"id": 1, "first_name": "John", "last_name": "Doe",
                    "email": "john@example.com", "site_id": 10}]},
        # _get_last_report_time
        {"rows": [{"value": "2024-01-01T00:00:00"}]},
        # _get_site_name
        {"rows": [{"name": "Main Office"}]},
        # _new_issues
        {"rows": []},
        # _vendor_visits_today
        {"rows": []},
        # _important_since (5 queries — one per entity type)
        {"rows": []}, {"rows": []}, {"rows": []}, {"rows": []}, {"rows": []},
        # _set_last_report_time (INSERT/UPSERT)
        {"rowcount": 1, "lastrowid": 1},
    ]

    result = generate_and_send_daily_reports(instance_id=42)

    assert len(result) == 1
    assert result[0]["supervisor"] == "John Doe"
    assert result[0]["success"] is True
    mock_send.assert_called_once()
