#!/usr/bin/env python3
"""Initialize PostgreSQL for MileCore: start service, create user/database, verify connection."""

import subprocess
import sys
from urllib.parse import urlparse

# ---------------------------------------------------------------------------
# Configuration — read DATABASE_URL the same way backend/config.py does,
# but without importing it (avoids pulling in dotenv / venv dependencies).
# ---------------------------------------------------------------------------
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://truecore:truecore@localhost:5432/truecore",
)

parsed = urlparse(DATABASE_URL)
DB_USER = parsed.username or "truecore"
DB_PASS = parsed.password or "truecore"
DB_HOST = parsed.hostname or "localhost"
DB_PORT = str(parsed.port or 5432)
DB_NAME = parsed.path.lstrip("/") or "truecore"


def run(cmd, **kwargs):
    """Run a shell command and return the CompletedProcess."""
    return subprocess.run(cmd, capture_output=True, text=True, **kwargs)


def psql_as_postgres(sql, dbname="postgres"):
    """Execute SQL as the postgres superuser and return stdout."""
    result = run(["sudo", "-u", "postgres", "psql", "-d", dbname, "-tAc", sql])
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    return result.stdout.strip()


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------

def check_pg_running():
    """Return True if PostgreSQL is accepting connections."""
    result = run(["pg_isready", "-h", DB_HOST, "-p", DB_PORT])
    return result.returncode == 0


def start_postgresql():
    print("  Starting PostgreSQL service …")
    result = run(["sudo", "service", "postgresql", "start"])
    if result.returncode != 0:
        print(f"  X  Failed to start PostgreSQL: {result.stderr.strip()}")
        return False
    if not check_pg_running():
        print("  X  PostgreSQL still not accepting connections after start.")
        return False
    return True


def ensure_user():
    exists = psql_as_postgres(f"SELECT 1 FROM pg_roles WHERE rolname='{DB_USER}'")
    if exists == "1":
        print(f"  OK User '{DB_USER}' already exists.")
        return
    psql_as_postgres(f"CREATE USER {DB_USER} WITH PASSWORD '{DB_PASS}'")
    print(f"  OK Created user '{DB_USER}'.")


def ensure_database():
    exists = psql_as_postgres(f"SELECT 1 FROM pg_database WHERE datname='{DB_NAME}'")
    if exists == "1":
        print(f"  OK Database '{DB_NAME}' already exists.")
        return
    psql_as_postgres(f"CREATE DATABASE {DB_NAME} OWNER {DB_USER}")
    print(f"  OK Created database '{DB_NAME}' with owner '{DB_USER}'.")


def grant_privileges():
    psql_as_postgres(f"GRANT ALL ON SCHEMA public TO {DB_USER}", dbname=DB_NAME)
    print(f"  OK Granted privileges on schema public to '{DB_USER}'.")


def verify_connection():
    result = run([
        "psql", DATABASE_URL, "-tAc", "SELECT 1",
    ])
    if result.returncode == 0 and result.stdout.strip() == "1":
        print(f"  OK Connection verified ({DATABASE_URL})")
        return True
    print(f"  X  Connection failed: {result.stderr.strip()}")
    return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print(f"MileCore DB init  ({DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME})\n")

    # 1. PostgreSQL running?
    if check_pg_running():
        print("  OK PostgreSQL is running.")
    else:
        print("  -- PostgreSQL is not running.")
        if not start_postgresql():
            sys.exit(1)
        print("  OK PostgreSQL is running.")

    # 2. User
    try:
        ensure_user()
    except RuntimeError as e:
        print(f"  X  Failed to ensure user: {e}")
        sys.exit(1)

    # 3. Database
    try:
        ensure_database()
    except RuntimeError as e:
        print(f"  X  Failed to ensure database: {e}")
        sys.exit(1)

    # 4. Privileges
    try:
        grant_privileges()
    except RuntimeError as e:
        print(f"  X  Failed to grant privileges: {e}")
        sys.exit(1)

    # 5. Verify
    if not verify_connection():
        sys.exit(1)

    print("\nDone — database is ready.")


if __name__ == "__main__":
    main()
