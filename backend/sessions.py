import json
import uuid
from typing import Any

from backend.database import _get_pool, _set_instance


def create_session(person_id: int = 1, instance_id: int = 1) -> str:
    session_id = str(uuid.uuid4())
    pool = _get_pool()
    with pool.connection() as conn:
        _set_instance(conn, instance_id)
        conn.execute(
            "INSERT INTO chat_sessions (id, person_id, instance_id) VALUES (%s, %s, %s)",
            [session_id, person_id, instance_id],
        )
        conn.commit()
    return session_id


def get_session(session_id: str, instance_id: int = 1) -> list[dict[str, Any]] | None:
    pool = _get_pool()
    with pool.connection() as conn:
        _set_instance(conn, instance_id)
        row = conn.execute(
            "SELECT id FROM chat_sessions WHERE id = %s AND instance_id = %s",
            [session_id, instance_id],
        ).fetchone()
        if row is None:
            return None

        rows = conn.execute(
            "SELECT role, content FROM chat_messages WHERE session_id = %s AND instance_id = %s ORDER BY id",
            [session_id, instance_id],
        ).fetchall()
    return [{"role": r["role"], "content": json.loads(r["content"])} for r in rows]


def save_history(session_id: str, messages: list[dict[str, Any]], instance_id: int = 1) -> None:
    """Persist new messages from the full history list."""
    pool = _get_pool()
    with pool.connection() as conn:
        _set_instance(conn, instance_id)
        existing_count = conn.execute(
            "SELECT COUNT(*) AS cnt FROM chat_messages WHERE session_id = %s AND instance_id = %s",
            [session_id, instance_id],
        ).fetchone()["cnt"]

        new_messages = messages[existing_count:]
        for msg in new_messages:
            conn.execute(
                "INSERT INTO chat_messages (session_id, role, content, instance_id) VALUES (%s, %s, %s, %s)",
                [session_id, msg["role"], json.dumps(msg["content"]), instance_id],
            )

        # Auto-set title from first user message if not set
        if existing_count == 0 and new_messages:
            for msg in new_messages:
                if msg["role"] == "user" and isinstance(msg["content"], str):
                    title = msg["content"][:60]
                    conn.execute(
                        "UPDATE chat_sessions SET title = %s WHERE id = %s AND instance_id = %s",
                        [title, session_id, instance_id],
                    )
                    break

        conn.execute(
            "UPDATE chat_sessions SET updated_at = NOW() WHERE id = %s AND instance_id = %s",
            [session_id, instance_id],
        )
        conn.commit()


def list_sessions(person_id: int = 1, instance_id: int = 1) -> list[dict[str, Any]]:
    pool = _get_pool()
    with pool.connection() as conn:
        _set_instance(conn, instance_id)
        rows = conn.execute(
            "SELECT id, title, created_at, updated_at FROM chat_sessions "
            "WHERE person_id IS NOT DISTINCT FROM %s AND instance_id = %s ORDER BY updated_at DESC",
            [person_id, instance_id],
        ).fetchall()
    return [
        {"id": r["id"], "title": r["title"], "created_at": r["created_at"], "updated_at": r["updated_at"]}
        for r in rows
    ]
