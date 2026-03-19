"""Tests for backend/claude_client.py — email gating, query limits, role blocking, rule matching."""

import json
from unittest.mock import patch

from backend.claude_client import (
    _find_matching_rule,
    _build_user_role_section,
    _build_current_user_section,
    _increment_query_count,
    _execute_tools,
)


# --- Rule matching (pure) ----------------------------------------------------

def test_find_matching_rule_insert():
    rules = [{"id": 1, "description": "INSERT into PEOPLE requires approval"}]
    result = _find_matching_rule("INSERT INTO people (name) VALUES ('test')", rules)
    assert result == rules[0]


def test_find_matching_rule_no_match():
    rules = [{"id": 1, "description": "INSERT into PEOPLE requires approval"}]
    result = _find_matching_rule("SELECT * FROM people", rules)
    assert result is None


def test_find_matching_rule_wrong_table():
    rules = [{"id": 1, "description": "INSERT into PEOPLE requires approval"}]
    result = _find_matching_rule("INSERT INTO sites (name) VALUES ('test')", rules)
    assert result is None


# --- User role section (pure) ------------------------------------------------

def test_build_user_role_section_admin():
    result = _build_user_role_section("admin")
    assert "can manage approval rules" in result.lower()


def test_build_user_role_section_owner():
    result = _build_user_role_section("owner")
    assert "can manage approval rules" in result.lower()


def test_build_user_role_section_user():
    result = _build_user_role_section("user")
    assert "CANNOT" in result


# --- Current user section (pure) ---------------------------------------------

def test_build_current_user_section_none():
    result = _build_current_user_section(None)
    assert "No current user record" in result


def test_build_current_user_section_data():
    user = {
        "person_id": 42,
        "display_name": "Alice",
        "username": "alice",
        "role": "admin",
        "email": "alice@example.com",
        "phone": "555-1234",
        "role_title": "Manager",
        "department": "IT",
        "site_id": 1,
        "site_name": "Main Office",
        "team_id": 2,
        "team_name": "Tech Support",
    }
    result = _build_current_user_section(user)
    assert "42" in result              # person_id
    assert "Alice" in result           # display_name
    assert "alice@example.com" in result  # email
    assert "alice" in result           # username
    assert "Manager" in result         # role_title
    assert "IT" in result              # department
    assert "Main Office" in result     # site_name
    assert "Tech Support" in result    # team_name
    assert "555-1234" in result        # phone


# --- Query limit --------------------------------------------------------------

@patch("backend.claude_client.execute_query")
def test_increment_query_count_ok(mock_eq):
    mock_eq.side_effect = [
        {"rows": [{"query_count": 5, "query_limit": 250}]},  # SELECT
        {"rowcount": 1, "lastrowid": None},                   # UPDATE
    ]

    result = _increment_query_count(instance_id=42)

    assert result is None
    assert mock_eq.call_count == 2


@patch("backend.claude_client.execute_query")
def test_increment_query_count_blocked(mock_eq):
    mock_eq.return_value = {"rows": [{"query_count": 250, "query_limit": 250}]}

    result = _increment_query_count(instance_id=42)

    assert result is not None
    assert "error" in result
    assert result["error"] == "Query limit reached"
    assert mock_eq.call_count == 1  # Only SELECT, no UPDATE


@patch("backend.claude_client.execute_query")
def test_increment_query_count_instance_not_found(mock_eq):
    mock_eq.return_value = {"rows": []}

    result = _increment_query_count(instance_id=999)

    assert result is not None
    assert result["error"] == "Instance not found"
    assert mock_eq.call_count == 1


# --- Tool execution: execute_sql ----------------------------------------------

@patch("backend.claude_client.execute_query")
def test_execute_sql_select(mock_eq):
    mock_eq.return_value = {"columns": ["id", "name"], "rows": [{"id": 1, "name": "Alice"}], "rowcount": 1}

    assistant_content = [{
        "type": "tool_use",
        "id": "t1",
        "name": "execute_sql",
        "input": {"sql": "SELECT * FROM people", "explanation": "List people"},
    }]
    sql_log = []

    results = _execute_tools(assistant_content, sql_log, user_role="admin", instance_id=42)

    assert len(results) == 1
    content = json.loads(results[0]["content"])
    assert content["rows"] == [{"id": 1, "name": "Alice"}]
    assert len(sql_log) == 1
    assert sql_log[0]["sql"] == "SELECT * FROM people"


@patch("backend.claude_client.execute_query")
def test_execute_sql_write_no_matching_rule(mock_eq):
    mock_eq.side_effect = [
        {"rows": []},                        # SELECT approval_rules (no rules)
        {"rowcount": 1, "lastrowid": 5},     # INSERT INTO people
    ]

    assistant_content = [{
        "type": "tool_use",
        "id": "t1",
        "name": "execute_sql",
        "input": {"sql": "INSERT INTO people (first_name) VALUES ('Alice')", "explanation": "Add person"},
    }]
    sql_log = []

    results = _execute_tools(assistant_content, sql_log, user_role="admin", instance_id=42)

    assert len(results) == 1
    content = json.loads(results[0]["content"])
    assert content["lastrowid"] == 5
    assert len(sql_log) == 1


@patch("backend.claude_client.validate_query")
@patch("backend.claude_client.execute_query")
def test_execute_sql_write_with_approval_rule(mock_eq, mock_validate):
    mock_validate.return_value = {"valid": True, "rowcount": 0}
    mock_eq.side_effect = [
        # SELECT approval_rules — returns a matching rule
        {"rows": [{"id": 1, "description": "INSERT into PEOPLE requires approval"}]},
        # INSERT INTO pending_approvals
        {"rowcount": 1, "lastrowid": 99},
    ]

    assistant_content = [{
        "type": "tool_use",
        "id": "t1",
        "name": "execute_sql",
        "input": {"sql": "INSERT INTO people (first_name) VALUES ('Alice')", "explanation": "Add person"},
    }]
    sql_log = []

    results = _execute_tools(assistant_content, sql_log, user_role="admin", instance_id=42)

    assert len(results) == 1
    content = json.loads(results[0]["content"])
    assert content["queued"] is True
    assert content["executed"] is False
    assert content["approval_id"] == 99
    mock_validate.assert_called_once()


# --- Tool execution: email gating ---------------------------------------------

@patch("backend.claude_client.smtp_send_email")
@patch("backend.claude_client.execute_query")
def test_email_tool_blocked_when_addon_disabled(mock_eq, mock_smtp):
    mock_eq.return_value = {"rows": [{"email_addon": False, "email_signature": ""}]}

    assistant_content = [{
        "type": "tool_use",
        "id": "t1",
        "name": "send_email",
        "input": {"to_email": "a@b.com", "subject": "hi", "body": "hello"},
    }]
    sql_log = []

    results = _execute_tools(assistant_content, sql_log, user_role="admin", instance_id=42)

    assert len(results) == 1
    content = json.loads(results[0]["content"])
    assert "error" in content
    assert "not enabled" in content["error"]
    mock_smtp.assert_not_called()


@patch("backend.claude_client.smtp_send_email")
@patch("backend.claude_client.execute_query")
def test_email_tool_sends_when_addon_enabled(mock_eq, mock_smtp):
    mock_eq.return_value = {"rows": [{"email_addon": True, "email_signature": "-- Sent via TrueCore"}]}
    mock_smtp.return_value = {"success": True}

    assistant_content = [{
        "type": "tool_use",
        "id": "t1",
        "name": "send_email",
        "input": {"to_email": "a@b.com", "subject": "hi", "body": "hello"},
    }]
    sql_log = []

    results = _execute_tools(assistant_content, sql_log, user_role="admin", instance_id=42)

    assert len(results) == 1
    content = json.loads(results[0]["content"])
    assert content["success"] is True
    mock_smtp.assert_called_once()
    # Verify signature was appended to body
    call_kwargs = mock_smtp.call_args
    assert "-- Sent via TrueCore" in call_kwargs.kwargs["body"]


# --- Tool execution: admin-only blocking --------------------------------------

@patch("backend.claude_client.execute_query")
def test_admin_only_tool_blocked_for_user(mock_eq):
    assistant_content = [{
        "type": "tool_use",
        "id": "t1",
        "name": "manage_approval_rules",
        "input": {"action": "list"},
    }]
    sql_log = []

    results = _execute_tools(assistant_content, sql_log, user_role="user", instance_id=42)

    assert len(results) == 1
    content = json.loads(results[0]["content"])
    assert "error" in content
    assert "admin access" in content["error"]
    mock_eq.assert_not_called()
