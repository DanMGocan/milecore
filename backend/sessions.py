import json
import uuid
from typing import Any

from backend.database import get_connection, _lock


def create_session(user_id: int = 1) -> str:
    session_id = str(uuid.uuid4())
    conn = get_connection()
    with _lock:
        conn.execute(
            "INSERT INTO chat_sessions (id, user_id) VALUES (?, ?)",
            [session_id, user_id],
        )
        conn.commit()
    return session_id


def get_session(session_id: str) -> list[dict[str, Any]] | None:
    conn = get_connection()
    with _lock:
        # Check session exists
        row = conn.execute(
            "SELECT id FROM chat_sessions WHERE id = ?", [session_id]
        ).fetchone()
        if row is None:
            return None

        rows = conn.execute(
            "SELECT role, content FROM chat_messages WHERE session_id = ? ORDER BY id",
            [session_id],
        ).fetchall()
    return [{"role": r[0], "content": json.loads(r[1])} for r in rows]


def save_history(session_id: str, messages: list[dict[str, Any]]) -> None:
    """Persist new messages from the full history list."""
    conn = get_connection()
    with _lock:
        existing_count = conn.execute(
            "SELECT COUNT(*) FROM chat_messages WHERE session_id = ?", [session_id]
        ).fetchone()[0]

        new_messages = messages[existing_count:]
        for msg in new_messages:
            conn.execute(
                "INSERT INTO chat_messages (session_id, role, content) VALUES (?, ?, ?)",
                [session_id, msg["role"], json.dumps(msg["content"])],
            )

        # Auto-set title from first user message if not set
        if existing_count == 0 and new_messages:
            for msg in new_messages:
                if msg["role"] == "user" and isinstance(msg["content"], str):
                    title = msg["content"][:60]
                    conn.execute(
                        "UPDATE chat_sessions SET title = ? WHERE id = ?",
                        [title, session_id],
                    )
                    break

        conn.execute(
            "UPDATE chat_sessions SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            [session_id],
        )
        conn.commit()


def list_sessions(user_id: int = 1) -> list[dict[str, Any]]:
    conn = get_connection()
    with _lock:
        rows = conn.execute(
            "SELECT id, title, created_at, updated_at FROM chat_sessions "
            "WHERE user_id = ? ORDER BY updated_at DESC",
            [user_id],
        ).fetchall()
    return [
        {"id": r[0], "title": r[1], "created_at": r[2], "updated_at": r[3]}
        for r in rows
    ]
