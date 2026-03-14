#!/usr/bin/env python3
"""MileCore entry point. Wipes and reinitializes database on every run, then starts the server."""

import os
import subprocess
import sys

from dotenv import load_dotenv

load_dotenv()


def build_frontend():
    frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
    node_modules = os.path.join(frontend_dir, "node_modules")
    if not os.path.isdir(node_modules):
        print("Installing frontend dependencies...")
        subprocess.run(["npm", "install"], cwd=frontend_dir, check=True)
    print("Building frontend...")
    subprocess.run(["npm", "run", "build"], cwd=frontend_dir, check=True)


def main():
    # Validate API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key or api_key == "your-api-key-here":
        print("ERROR: Please set ANTHROPIC_API_KEY in your .env file")
        sys.exit(1)

    spare_key = os.getenv("ANTHROPIC_API_KEY_SPARE")
    if spare_key:
        print("Spare API key configured (will be used as fallback)")
    else:
        print("No spare API key configured (set ANTHROPIC_API_KEY_SPARE for fallback)")

    db_path = os.getenv("DATABASE_PATH", "milecore.db")
    schema_path = os.getenv("SCHEMA_PATH", "schema.sql")

    from backend.database import init_db
    from initial_seed import seed_initial_data

    for f in [db_path, db_path + "-shm", db_path + "-wal"]:
        if os.path.exists(f):
            os.remove(f)
    print(f"Initializing fresh database: {db_path}")
    init_db(schema_path)

    print("Applying initial seed...")
    seed_initial_data()

    # Build frontend
    build_frontend()

    # Start server
    print("\n========================================")
    print("  MileCore - Site Operations Assistant")
    print("  http://localhost:8000")
    print("========================================\n")

    import uvicorn
    uvicorn.run(
        "backend.app:create_app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        factory=True,
    )


if __name__ == "__main__":
    main()
