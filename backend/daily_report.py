"""Daily site operations report — sent to site supervisors each morning."""

from datetime import date, datetime, timedelta, timezone

from backend.database import get_connection, _lock
from backend.email_sender import send_email


def _get_last_report_time() -> str:
    """Return ISO timestamp of last report, or yesterday if never sent."""
    rows = _query_rows(
        "SELECT value FROM app_settings WHERE key = 'last_daily_report_at'"
    )
    if rows:
        return rows[0]["value"]
    return (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()


def _set_last_report_time() -> None:
    """Upsert current UTC time as last report timestamp."""
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    with _lock:
        conn.execute(
            "INSERT INTO app_settings (key, value) VALUES ('last_daily_report_at', ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            [now],
        )
        conn.commit()


def _query_rows(sql: str, params: list | None = None) -> list[dict]:
    conn = get_connection()
    with _lock:
        cursor = conn.execute(sql, params or [])
        columns = [d[0] for d in cursor.description] if cursor.description else []
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _get_supervisors() -> list[dict]:
    return _query_rows(
        "SELECT id, first_name, last_name, email, site_id FROM people "
        "WHERE is_supervisor = 1 AND email IS NOT NULL AND status = 'active'"
    )


def _get_site_name(site_id: int) -> str:
    rows = _query_rows("SELECT name FROM sites WHERE id = ?", [site_id])
    return rows[0]["name"] if rows else f"Site {site_id}"


def _new_issues(site_id: int) -> list[dict]:
    return _query_rows(
        "SELECT id, title, severity, symptom FROM technical_issues "
        "WHERE DATE(created_at) = DATE('now', '-1 day') AND site_id = ?",
        [site_id],
    )


def _vendor_visits_today(site_id: int) -> list[dict]:
    return _query_rows(
        "SELECT id, title, start_time, end_time, description FROM events "
        "WHERE DATE(start_time) = DATE('now') AND site_id = ? "
        "AND (LOWER(event_type) LIKE '%vendor%' OR LOWER(event_type) LIKE '%visit%')",
        [site_id],
    )


def _important_since(site_id: int, since: str) -> list[dict]:
    queries = [
        ("Issue", "SELECT id, title, created_at FROM technical_issues WHERE important=1 AND created_at > ? AND site_id=?"),
        ("Request", "SELECT id, title, opened_at as created_at FROM requests WHERE important=1 AND opened_at > ? AND site_id=?"),
        ("Event", "SELECT id, title, created_at FROM events WHERE important=1 AND created_at > ? AND site_id=?"),
        ("Note", "SELECT id, title, created_at FROM notes WHERE important=1 AND created_at > ? AND site_id=?"),
        ("Change", "SELECT id, title, created_at FROM changes WHERE important=1 AND created_at > ? AND site_id=?"),
    ]
    items = []
    for label, sql in queries:
        for row in _query_rows(sql, [since, site_id]):
            items.append({"type": label, "id": row["id"], "title": row.get("title", "—")})
    return items


def _format_report(site_name: str, issues: list, visits: list, important: list, since_date: str) -> str:
    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    lines = [
        f"Daily Site Operations Report — {site_name}",
        f"Report Date: {today}",
        "",
        f"NEW ISSUES ({yesterday})",
        "-" * 30,
    ]
    if issues:
        for i in issues:
            lines.append(f"  - [#{i['id']}] {i['title']} (severity: {i.get('severity', 'n/a')})")
    else:
        lines.append("  No new issues reported yesterday.")

    lines += [
        "",
        f"VENDOR VISITS ({today})",
        "-" * 30,
    ]
    if visits:
        for v in visits:
            time_str = v.get("start_time", "")
            lines.append(f"  - {v['title']} ({time_str})")
    else:
        lines.append("  No vendor visits scheduled today.")

    lines += [
        "",
        f"FLAGGED AS IMPORTANT (since {since_date})",
        "-" * 30,
    ]
    if important:
        for item in important:
            lines.append(f"  - [{item['type']} #{item['id']}] {item['title']}")
    else:
        lines.append("  No items flagged as important since last report.")

    return "\n".join(lines)


def generate_and_send_daily_reports() -> list[dict]:
    """Generate and send reports to all site supervisors. Returns send results."""
    supervisors = _get_supervisors()
    since = _get_last_report_time()
    since_date = since[:10]
    results = []
    any_sent = False

    for sup in supervisors:
        site_id = sup.get("site_id")
        if not site_id:
            continue

        site_name = _get_site_name(site_id)
        issues = _new_issues(site_id)
        visits = _vendor_visits_today(site_id)
        important = _important_since(site_id, since)

        body = _format_report(site_name, issues, visits, important, since_date)
        to_name = f"{sup['first_name']} {sup['last_name']}"
        subject = f"Daily Site Report — {site_name} — {date.today().isoformat()}"

        result = send_email(
            to_email=sup["email"],
            subject=subject,
            body=body,
            to_name=to_name,
        )
        if result.get("success"):
            any_sent = True
        results.append({"supervisor": to_name, "email": sup["email"], **result})

    if any_sent:
        _set_last_report_time()

    return results
