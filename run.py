#!/usr/bin/env python3
"""TrueCore.cloud entry point. Initializes PostgreSQL schema and starts the server."""

import os
import shutil
import subprocess
import sys

from dotenv import load_dotenv

load_dotenv()


def build_frontend():
    npm = shutil.which("npm")
    if npm is None:
        print("ERROR: npm not found in PATH")
        sys.exit(1)
    frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
    node_modules = os.path.join(frontend_dir, "node_modules")
    if not os.path.isdir(node_modules):
        print("Installing frontend dependencies...")
        subprocess.run([npm, "install"], cwd=frontend_dir, check=True)
    print("Building frontend...")
    subprocess.run([npm, "run", "build"], cwd=frontend_dir, check=True)


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

    database_url = os.getenv("DATABASE_URL", "postgresql://truecore:truecore@localhost:5432/truecore")
    schema_path = os.getenv("SCHEMA_PATH", "schema_pg.sql")

    from backend.database import init_pool, init_db, shutdown_pool, execute_query
    from initial_seed import seed_initial_data

    # Initialize the connection pool
    print(f"Connecting to PostgreSQL...")
    init_pool(database_url)

    # Initialize schema (CREATE TABLE IF NOT EXISTS equivalent — safe to re-run)
    print(f"Initializing database schema from {schema_path}...")
    init_db(schema_path)

    # Create default instance if it doesn't exist
    result = execute_query("SELECT id FROM instances WHERE id = 1", instance_id=None)
    if not result.get("rows"):
        print("Creating default instance...")
        execute_query(
            "INSERT INTO instances (name, slug, tier, status, query_count, query_limit) "
            "VALUES ('Default', 'default', 'free', 'active', 0, 60)",
            instance_id=None,
        )

    # Create test account if it doesn't exist
    result = execute_query("SELECT id FROM auth_users WHERE email = 'gocandan@gmail.com'", instance_id=None)
    if not result.get("rows"):
        import bcrypt
        pw_hash = bcrypt.hashpw(b"123", bcrypt.gensalt()).decode()
        res = execute_query(
            "INSERT INTO auth_users (email, password_hash, display_name, email_verified) "
            "VALUES ('gocandan@gmail.com', ?, 'Dan Gocan', true)",
            [pw_hash],
            instance_id=None,
        )
        user_id = res.get("lastrowid")
        if user_id:
            execute_query(
                "INSERT INTO instance_memberships (auth_user_id, instance_id, role) VALUES (?, 1, 'owner')",
                [user_id],
                instance_id=None,
            )
            # Set as billing owner
            execute_query(
                "UPDATE instances SET billing_owner_id = ? WHERE id = 1",
                [user_id],
                instance_id=None,
            )
            print(f"Created account: gocandan@gmail.com (owner of instance 1)")

    # Apply initial seed for instance 1
    print("Applying initial seed for default instance...")
    seed_initial_data(instance_id=1)

    # Close pool before starting uvicorn (it will create its own via lifespan)
    shutdown_pool()

    # Build frontend
    build_frontend()

    # Start server
    print("\n========================================")
    print("  TrueCore.cloud - Site Operations Assistant")
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
