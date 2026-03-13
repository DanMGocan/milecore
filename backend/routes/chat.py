import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend import sessions
from backend.claude_client import chat, chat_stream
from backend.database import get_home_site

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    response: str
    session_id: str
    sql_executed: list


@router.get("/home-site")
async def home_site_endpoint():
    site = get_home_site()
    return {"home_site": site}


@router.get("/user")
async def get_user():
    return {"username": "dan", "display_name": "Dan", "role": "admin"}


@router.get("/sessions")
async def list_sessions_endpoint():
    return {"sessions": sessions.list_sessions()}


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
    if not session_id or sessions.get_session(session_id) is None:
        session_id = sessions.create_session()

    history = sessions.get_session(session_id) or []
    state = {}

    def generate():
        yield f"event: session\ndata: {json.dumps({'session_id': session_id})}\n\n"
        yield from chat_stream(req.message, history, state)
        if "history" in state:
            sessions.save_history(session_id, state["history"])

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    session_id = req.session_id
    if not session_id or sessions.get_session(session_id) is None:
        session_id = sessions.create_session()

    history = sessions.get_session(session_id) or []
    result = chat(req.message, history)
    sessions.save_history(session_id, result["history"])

    return ChatResponse(
        response=result["response"],
        session_id=session_id,
        sql_executed=result["sql_executed"],
    )


@router.post("/admin/send-daily-report")
async def trigger_daily_report():
    from backend.daily_report import generate_and_send_daily_reports
    result = generate_and_send_daily_reports()
    return {"status": "sent", "details": result}
