import json

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend import sessions
from backend.claude_client import chat, chat_stream
from backend.database import execute_query, get_home_site

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    person_id: int = 1


class ChatResponse(BaseModel):
    response: str
    session_id: str
    sql_executed: list


def _get_current_user(person_id: int) -> dict | None:
    result = execute_query(
        """
        SELECT
            p.id AS person_id,
            p.username,
            p.first_name,
            p.last_name,
            p.email,
            p.phone,
            p.role_title,
            p.department,
            p.site_id,
            p.team_id,
            p.user_role AS role,
            s.name AS site_name,
            t.name AS team_name
        FROM people p
        LEFT JOIN sites s ON s.id = p.site_id
        LEFT JOIN teams t ON t.id = p.team_id
        WHERE p.id = ? AND p.is_user = 1
        """,
        [person_id],
    )
    if not result.get("rows"):
        return None
    row = result["rows"][0]
    return {
        "person_id": row["person_id"],
        "username": row["username"],
        "display_name": f"{row['first_name']} {row['last_name']}".strip(),
        "email": row["email"],
        "phone": row["phone"],
        "role_title": row["role_title"],
        "department": row["department"],
        "site_id": row["site_id"],
        "team_id": row["team_id"],
        "site_name": row["site_name"],
        "team_name": row["team_name"],
        "role": row["role"],
    }


@router.get("/home-site")
async def home_site_endpoint():
    site = get_home_site()
    return {"home_site": site}


@router.get("/user")
async def get_user(person_id: int = Query(1)):
    current_user = _get_current_user(person_id)
    if not current_user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "person_id": current_user["person_id"],
        "username": current_user["username"],
        "display_name": current_user["display_name"].split(" ")[0],
        "job_title": current_user["role_title"],
        "role": current_user["role"],
    }


@router.get("/sessions")
async def list_sessions_endpoint(person_id: int = Query(1)):
    return {"sessions": sessions.list_sessions(person_id)}


@router.get("/sessions/{session_id}")
async def get_session_endpoint(session_id: str):
    history = sessions.get_session(session_id)
    if history is None:
        raise HTTPException(status_code=404, detail="Session not found")
    display_messages = []
    for msg in history:
        if msg["role"] == "user":
            if isinstance(msg["content"], str):
                display_messages.append({"role": "user", "text": msg["content"]})
        elif msg["role"] == "assistant":
            content = msg["content"]
            if isinstance(content, list):
                text_parts = [b["text"] for b in content if isinstance(b, dict) and b.get("type") == "text"]
                if text_parts:
                    display_messages.append({"role": "assistant", "text": "\n".join(text_parts)})
            elif isinstance(content, str):
                display_messages.append({"role": "assistant", "text": content})
    return {"messages": display_messages, "session_id": session_id}


@router.post("/chat/stream")
async def chat_stream_endpoint(req: ChatRequest):
    session_id = req.session_id
    person_id = req.person_id
    history = sessions.get_session(session_id) if session_id else None
    if history is None:
        session_id = sessions.create_session(person_id)
        history = []

    current_user = _get_current_user(person_id)
    user_role = current_user["role"] if current_user else "user"
    state = {}

    def generate():
        yield f"event: session\ndata: {json.dumps({'session_id': session_id})}\n\n"
        yield from chat_stream(req.message, history, state, user_role, current_user)
        if "history" in state:
            sessions.save_history(session_id, state["history"])

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    session_id = req.session_id
    person_id = req.person_id
    history = sessions.get_session(session_id) if session_id else None
    if history is None:
        session_id = sessions.create_session(person_id)
        history = []

    current_user = _get_current_user(person_id)
    user_role = current_user["role"] if current_user else "user"
    result = chat(req.message, history, user_role, current_user)
    sessions.save_history(session_id, result["history"])

    return ChatResponse(
        response=result["response"],
        session_id=session_id,
        sql_executed=result["sql_executed"],
    )


@router.get("/approvals/pending-count")
async def pending_approvals_count():
    result = execute_query("SELECT COUNT(*) as count FROM pending_approvals WHERE status = 'pending'")
    count = result["rows"][0]["count"] if result.get("rows") else 0
    return {"pending_count": count}


@router.post("/admin/send-daily-report")
async def trigger_daily_report():
    from backend.daily_report import generate_and_send_daily_reports
    result = generate_and_send_daily_reports()
    return {"status": "sent", "details": result}
