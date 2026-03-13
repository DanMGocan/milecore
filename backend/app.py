import asyncio
import os
from contextlib import asynccontextmanager
from datetime import datetime, time, timedelta

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.config import DAILY_REPORT_HOUR, DAILY_REPORT_MINUTE
from backend.routes.chat import router as chat_router
from backend.routes.database_browser import router as browser_router
from backend.routes.upload import router as upload_router
from backend.routes.dashboard import router as dashboard_router


async def _daily_report_loop():
    """Sleep until the configured time each day, then send reports."""
    while True:
        now = datetime.now()
        target = datetime.combine(now.date(), time(DAILY_REPORT_HOUR, DAILY_REPORT_MINUTE))
        if now >= target:
            target += timedelta(days=1)
        await asyncio.sleep((target - now).total_seconds())
        try:
            from backend.daily_report import generate_and_send_daily_reports
            generate_and_send_daily_reports()
            print(f"[{datetime.now().isoformat()}] Daily reports sent.")
        except Exception as e:
            print(f"[{datetime.now().isoformat()}] Daily report error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_daily_report_loop())
    yield
    task.cancel()


def create_app() -> FastAPI:
    app = FastAPI(
        title="MileCore",
        description="Site Operations AI Database Assistant",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(chat_router, prefix="/api")
    app.include_router(browser_router, prefix="/api")
    app.include_router(upload_router, prefix="/api")
    app.include_router(dashboard_router, prefix="/api")

    # Serve Vite build output
    frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
    dist_dir = os.path.join(frontend_dir, "dist")
    assets_dir = os.path.join(dist_dir, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{path:path}")
    async def serve_spa(path: str):
        dist_index = os.path.join(dist_dir, "index.html")
        if os.path.isfile(dist_index):
            return FileResponse(dist_index)
        return FileResponse(os.path.join(frontend_dir, "index.html"))

    return app
