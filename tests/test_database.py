"""Tests for backend/database.py — placeholder translation (pure function)."""

from backend.database import _translate_placeholders


def test_no_placeholders():
    sql = "SELECT * FROM users"
    assert _translate_placeholders(sql) == sql


def test_simple_replacement():
    assert _translate_placeholders("WHERE id = ?") == "WHERE id = %s"


def test_multiple_placeholders():
    assert _translate_placeholders("VALUES (?, ?)") == "VALUES (%s, %s)"


def test_quoted_string_preserved():
    sql = "SELECT * FROM t WHERE name = 'hello?' AND id = ?"
    result = _translate_placeholders(sql)
    assert result == "SELECT * FROM t WHERE name = 'hello?' AND id = %s"


def test_escaped_quotes():
    sql = "SELECT * FROM t WHERE name = 'it''s?' AND id = ?"
    result = _translate_placeholders(sql)
    assert result == "SELECT * FROM t WHERE name = 'it''s?' AND id = %s"


def test_double_quoted_identifier_preserved():
    sql = 'SELECT * FROM t WHERE "column?" = ? AND id = ?'
    result = _translate_placeholders(sql)
    assert result == 'SELECT * FROM t WHERE "column?" = %s AND id = %s'
