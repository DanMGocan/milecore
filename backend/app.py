import asyncio
import os
from contextlib import asynccontextmanager
from datetime import datetime, time, timedelta

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.config import CORS_ORIGINS, DATABASE_URL, DAILY_REPORT_HOUR, DAILY_REPORT_MINUTE
from backend.database import init_pool, shutdown_pool, execute_query
from backend.routes.auth_routes import router as auth_router
from backend.routes.instance_routes import router as instance_router
from backend.routes.chat import router as chat_router
from backend.routes.database_browser import router as browser_router
from backend.routes.upload import router as upload_router
from backend.routes.dashboard import router as dashboard_router
from backend.routes.billing_routes import router as billing_router


async def _daily_report_loop():
    """Sleep until the configured time each day, then send reports for all active instances."""
    while True:
        now = datetime.now()
        target = datetime.combine(now.date(), time(DAILY_REPORT_HOUR, DAILY_REPORT_MINUTE))
        if now >= target:
            target += timedelta(days=1)
        await asyncio.sleep((target - now).total_seconds())
        try:
            from backend.daily_report import generate_and_send_daily_reports
            # Get all active instances and send reports for each
            result = execute_query(
                "SELECT id FROM instances WHERE status = 'active' AND daily_reports_addon = true",
                instance_id=None,
            )
            instance_ids = [r["id"] for r in result.get("rows", [])]
            for iid in instance_ids:
                try:
                    generate_and_send_daily_reports(instance_id=iid)
                except Exception as e:
                    print(f"[{datetime.now().isoformat()}] Daily report error for instance {iid}: {e}")
            print(f"[{datetime.now().isoformat()}] Daily reports sent for {len(instance_ids)} instance(s).")
        except Exception as e:
            print(f"[{datetime.now().isoformat()}] Daily report error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize connection pool on startup
    init_pool(DATABASE_URL)
    task = asyncio.create_task(_daily_report_loop())
    yield
    task.cancel()
    shutdown_pool()


def create_app() -> FastAPI:
    app = FastAPI(
        title="TrueCore.cloud",
        description="Site Operations AI Database Assistant",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Auth routes (no auth required)
    app.include_router(auth_router, prefix="/api")
    app.include_router(instance_router, prefix="/api")

    # App routes
    app.include_router(chat_router, prefix="/api")
    app.include_router(browser_router, prefix="/api")
    app.include_router(upload_router, prefix="/api")
    app.include_router(dashboard_router, prefix="/api")
    app.include_router(billing_router, prefix="/api")

    # Serve Vite build output
    frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
    dist_dir = os.path.join(frontend_dir, "dist")
    assets_dir = os.path.join(dist_dir, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    dummy_dir = os.path.join(os.path.dirname(__file__), "..", "dummy_files")
    if os.path.isdir(dummy_dir):
        app.mount("/dummy_files", StaticFiles(directory=dummy_dir), name="dummy_files")

    @app.get("/{path:path}")
    async def serve_spa(path: str):
        dist_index = os.path.join(dist_dir, "index.html")
        if os.path.isfile(dist_index):
            return FileResponse(dist_index)
        return FileResponse(os.path.join(frontend_dir, "index.html"))

    return app
