import json
import uuid
from typing import Any

from backend.database import get_connection, _lock


def create_session(person_id: int = 1, instance_id: int = 1) -> str:
    session_id = str(uuid.uuid4())
    conn = get_connection()
    with _lock:
        conn.execute(
            "INSERT INTO chat_sessions (id, person_id, instance_id) VALUES (?, ?, ?)",
            [session_id, person_id, instance_id],
        )
        conn.commit()
    return session_id


def get_session(session_id: str, instance_id: int = 1) -> list[dict[str, Any]] | None:
    conn = get_connection()
    with _lock:
        # Check session exists
        row = conn.execute(
            "SELECT id FROM chat_sessions WHERE id = ? AND instance_id = ?",
            [session_id, instance_id],
        ).fetchone()
        if row is None:
            return None

        rows = conn.execute(
            "SELECT role, content FROM chat_messages WHERE session_id = ? AND instance_id = ? ORDER BY id",
            [session_id, instance_id],
        ).fetchall()
    return [{"role": r[0], "content": json.loads(r[1])} for r in rows]


def save_history(session_id: str, messages: list[dict[str, Any]], instance_id: int = 1) -> None:
    """Persist new messages from the full history list."""
    conn = get_connection()
    with _lock:
        existing_count = conn.execute(
            "SELECT COUNT(*) FROM chat_messages WHERE session_id = ? AND instance_id = ?",
            [session_id, instance_id],
        ).fetchone()[0]

        new_messages = messages[existing_count:]
        for msg in new_messages:
            conn.execute(
                "INSERT INTO chat_messages (session_id, role, content, instance_id) VALUES (?, ?, ?, ?)",
                [session_id, msg["role"], json.dumps(msg["content"]), instance_id],
            )

        # Auto-set title from first user message if not set
        if existing_count == 0 and new_messages:
            for msg in new_messages:
                if msg["role"] == "user" and isinstance(msg["content"], str):
                    title = msg["content"][:60]
                    conn.execute(
                        "UPDATE chat_sessions SET title = ? WHERE id = ? AND instance_id = ?",
                        [title, session_id, instance_id],
                    )
                    break

        conn.execute(
            "UPDATE chat_sessions SET updated_at = NOW() WHERE id = ? AND instance_id = ?",
            [session_id, instance_id],
        )
        conn.commit()


def list_sessions(person_id: int = 1, instance_id: int = 1) -> list[dict[str, Any]]:
    conn = get_connection()
    with _lock:
        rows = conn.execute(
            "SELECT id, title, created_at, updated_at FROM chat_sessions "
            "WHERE person_id = ? AND instance_id = ? ORDER BY updated_at DESC",
            [person_id, instance_id],
        ).fetchall()
    return [
        {"id": r[0], "title": r[1], "created_at": r[2], "updated_at": r[3]}
        for r in rows
    ]
