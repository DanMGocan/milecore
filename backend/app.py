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
from backend.routes.inbound_email_routes import router as inbound_email_router
from backend.routes.reminders_routes import router as reminders_router
from backend.routes.admin_routes import router as admin_router
from backend.routes.ticket_routes import router as ticket_router
from backend.routes.maintenance_routes import router as maintenance_router
from backend.routes.procurement_routes import router as procurement_router
from backend.routes.asset_routes import router as asset_router


async def _reminder_check_loop():
    """Check for due reminders every 60 seconds and send notification emails."""
    while True:
        await asyncio.sleep(60)
        try:
            from backend.reminders import process_due_reminders
            count = process_due_reminders()
            if count > 0:
                print(f"[{datetime.now().isoformat()}] Processed {count} reminder(s).")
        except Exception as e:
            print(f"[{datetime.now().isoformat()}] Reminder check error: {e}")


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


async def _maintenance_check_loop():
    """Check for due maintenance plans and inspections every 5 minutes."""
    while True:
        await asyncio.sleep(300)
        try:
            from backend.maintenance_scheduler import (
                process_due_maintenance_plans,
                process_due_inspections,
                check_overdue_work_orders,
            )
            wo_count = process_due_maintenance_plans()
            if wo_count > 0:
                print(f"[{datetime.now().isoformat()}] Generated {wo_count} work order(s).")
            ir_count = process_due_inspections()
            if ir_count > 0:
                print(f"[{datetime.now().isoformat()}] Generated {ir_count} inspection record(s).")
            overdue = check_overdue_work_orders()
            if overdue > 0:
                print(f"[{datetime.now().isoformat()}] Marked {overdue} work order(s) as overdue.")
        except Exception as e:
            print(f"[{datetime.now().isoformat()}] Maintenance check error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize connection pool on startup
    init_pool(DATABASE_URL)
    daily_task = asyncio.create_task(_daily_report_loop())
    reminder_task = asyncio.create_task(_reminder_check_loop())
    maintenance_task = asyncio.create_task(_maintenance_check_loop())
    yield
    daily_task.cancel()
    reminder_task.cancel()
    maintenance_task.cancel()
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
    app.include_router(inbound_email_router, prefix="/api")
    app.include_router(reminders_router, prefix="/api")
    app.include_router(admin_router, prefix="/api")
    app.include_router(ticket_router, prefix="/api")
    app.include_router(maintenance_router, prefix="/api")
    app.include_router(procurement_router, prefix="/api")
    app.include_router(asset_router, prefix="/api")

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
