import csv
import io
import json
import os
import re
import tempfile
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from backend.auth import InstanceContext, get_current_instance
from backend.config import (
    TICKET_ATTACHMENT_ALLOWED_TYPES,
    TICKET_ATTACHMENT_MAX_SIZE_MB,
)
from backend.database import execute_query, get_tables

router = APIRouter()

TEMP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "temp")
os.makedirs(TEMP_DIR, exist_ok=True)

# Local metadata dir for chat attachment file_id → S3 key resolution
_META_DIR = os.path.join(TEMP_DIR, "chat_meta")
os.makedirs(_META_DIR, exist_ok=True)


def _staged_path(file_id: str) -> str:
    """Return the on-disk path for a staged file."""
    return os.path.join(TEMP_DIR, f"{file_id}.json")


def _save_staged(file_id: str, data: dict) -> None:
    """Persist staged file data to disk."""
    with open(_staged_path(file_id), "w", encoding="utf-8") as f:
        json.dump(data, f)


def _load_staged(file_id: str) -> dict | None:
    """Load staged file data from disk. Returns None if not found."""
    path = _staged_path(file_id)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@router.post("/upload/stage")
async def stage_csv(file: UploadFile = File(...)):
    """Stage a CSV for AI-powered import. Returns summary for Claude to analyze."""
    if not file.filename or not file.filename.endswith((".csv", ".CSV")):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)

    if not rows:
        raise HTTPException(status_code=400, detail="CSV file is empty")

    file_id = str(uuid.uuid4())
    headers = list(rows[0].keys())
    _save_staged(file_id, {"rows": rows, "headers": headers, "filename": file.filename})

    return {
        "file_id": file_id,
        "filename": file.filename,
        "headers": headers,
        "sample_rows": rows[:3],
        "total_rows": len(rows),
    }


def import_staged_csv(file_id: str, table: str, column_mapping: dict[str, str], instance_id: int = 1) -> dict:
    """Import a staged CSV into the database with column remapping."""
    staged = _load_staged(file_id)
    if staged is None:
        return {"error": f"No staged file found with id {file_id}"}

    if not re.match(r"^\w+$", table):
        return {"error": f"Invalid table name: {table}"}

    rows_inserted = 0
    rows_skipped = 0
    errors = []

    for i, row in enumerate(staged["rows"]):
        mapped = {}
        for csv_col, table_col in column_mapping.items():
            if csv_col in row:
                mapped[table_col] = row[csv_col]

        mapped.pop("id", None)
        mapped.pop("instance_id", None)

        if not mapped:
            rows_skipped += 1
            continue

        # Add instance_id
        mapped["instance_id"] = instance_id
        columns = ", ".join([f'"{k}"' for k in mapped.keys()])
        placeholders = ", ".join(["?"] * len(mapped))
        values = list(mapped.values())
        sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
        result = execute_query(sql, values, instance_id=instance_id)

        if "error" in result:
            errors.append(f"Row {i + 1}: {result['error']}")
        elif result.get("rowcount", 0) == 0:
            rows_skipped += 1
        else:
            rows_inserted += 1

    return {
        "rows_inserted": rows_inserted,
        "rows_skipped": rows_skipped,
        "errors": errors,
    }


def remove_staged_file(file_id: str) -> None:
    """Remove a staged file after it has been successfully processed."""
    path = _staged_path(file_id)
    if os.path.exists(path):
        os.remove(path)


def generate_import_sql(file_id: str, table: str, column_mapping: dict[str, str], instance_id: int = 1) -> dict:
    """Generate a complete INSERT statement from a staged CSV."""
    staged = _load_staged(file_id)
    if staged is None:
        return {"error": f"No staged file found with id {file_id}"}
    if not re.match(r"^\w+$", table):
        return {"error": f"Invalid table name: {table}"}

    all_values = []
    skipped = 0
    for row in staged["rows"]:
        mapped = {}
        for csv_col, table_col in column_mapping.items():
            if csv_col in row:
                mapped[table_col] = row[csv_col]
        mapped.pop("id", None)
        if not mapped:
            skipped += 1
            continue
        all_values.append(mapped)

    if not all_values:
        return {"error": "No rows to import after mapping"}

    columns = list(all_values[0].keys())
    for col in columns:
        if not re.match(r"^\w+$", col):
            return {"error": f"Invalid column name: {col}"}
    # Add instance_id column
    columns.append("instance_id")
    col_list = ", ".join([f'"{c}"' for c in columns])

    def quote(v):
        if v is None or v == "":
            return "NULL"
        return "'" + str(v).replace("'", "''") + "'"

    row_strs = []
    for vals in all_values:
        row_strs.append("(" + ", ".join(quote(vals.get(c)) for c in columns[:-1]) + f", {instance_id})")

    sql = f"INSERT INTO {table} ({col_list}) VALUES\n" + ",\n".join(row_strs) + "\nON CONFLICT DO NOTHING"

    return {
        "sql": sql,
        "table": table,
        "total_rows": len(all_values),
        "skipped": skipped,
    }


@router.post("/upload")
async def upload_csv(file: UploadFile = File(...), table_name: str | None = None, ctx: InstanceContext = Depends(get_current_instance)):
    if not file.filename or not file.filename.endswith((".csv", ".CSV")):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)

    if not rows:
        raise HTTPException(status_code=400, detail="CSV file is empty")

    # If no table specified, use filename (without extension)
    if not table_name:
        table_name = file.filename.rsplit(".", 1)[0].lower().replace(" ", "_").replace("-", "_")

    # Create table if it doesn't exist
    existing = get_tables(instance_id=ctx.instance_id)
    if table_name not in existing:
        columns = rows[0].keys()
        col_defs = ", ".join([f'"{col}" TEXT' for col in columns])
        create_sql = f'CREATE TABLE {table_name} (id BIGSERIAL PRIMARY KEY, {col_defs}, instance_id BIGINT NOT NULL REFERENCES instances(id))'
        result = execute_query(create_sql, instance_id=ctx.instance_id)
        if "error" in result:
            raise HTTPException(status_code=400, detail=f"Failed to create table: {result['error']}")

    # Insert rows with instance_id
    inserted = 0
    errors = []
    for i, row in enumerate(rows):
        data_keys = list(row.keys()) + ["instance_id"]
        columns = ", ".join([f'"{k}"' for k in data_keys])
        placeholders = ", ".join(["?"] * len(data_keys))
        values = list(row.values()) + [ctx.instance_id]
        sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
        result = execute_query(sql, values, instance_id=ctx.instance_id)
        if "error" in result:
            errors.append(f"Row {i + 1}: {result['error']}")
        else:
            inserted += 1

    return {
        "message": f"Uploaded {inserted} rows to '{table_name}'",
        "table": table_name,
        "rows_inserted": inserted,
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# Image upload (S3 + AVIF conversion) for chat attachments
# ---------------------------------------------------------------------------

def get_chat_attachment_path(file_id: str, instance_id: int) -> dict | None:
    """Resolve a chat attachment file_id to its S3 metadata.

    Returns dict with s3_key, filename, content_type or None if not found.
    """
    meta_path = os.path.join(_META_DIR, f"{file_id}.json")
    if not os.path.isfile(meta_path):
        return None
    with open(meta_path, "r", encoding="utf-8") as f:
        return json.load(f)


def resolve_s3_attachment_for_email(file_id: str, instance_id: int) -> dict | None:
    """Download an S3 chat attachment to a temp file for email sending.

    Returns dict with path (temp file), filename, content_type or None.
    """
    from backend.s3_storage import download_image

    meta = get_chat_attachment_path(file_id, instance_id)
    if not meta or not meta.get("s3_key"):
        return None

    data, ct = download_image(meta["s3_key"])
    ext = meta["s3_key"].rsplit(".", 1)[-1] if "." in meta["s3_key"] else "avif"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}", dir=TEMP_DIR)
    tmp.write(data)
    tmp.close()

    return {
        "path": tmp.name,
        "filename": meta.get("filename", f"image.{ext}"),
        "content_type": ct,
    }


@router.post("/upload/file")
async def upload_file(file: UploadFile = File(...), ctx: InstanceContext = Depends(get_current_instance)):
    """Upload an image for attaching to emails or tickets. Converted to AVIF and stored in S3."""
    if not file.content_type or file.content_type not in TICKET_ATTACHMENT_ALLOWED_TYPES:
        allowed = ", ".join(TICKET_ATTACHMENT_ALLOWED_TYPES)
        raise HTTPException(status_code=400, detail=f"File type '{file.content_type}' not allowed. Allowed: {allowed}")

    content = await file.read()
    max_bytes = TICKET_ATTACHMENT_MAX_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(status_code=400, detail=f"File too large. Maximum size is {TICKET_ATTACHMENT_MAX_SIZE_MB} MB")

    from backend.s3_storage import upload_chat_image

    file_id = str(uuid.uuid4())
    original_filename = file.filename or "image"

    result = upload_chat_image(
        instance_id=ctx.instance_id,
        file_id=file_id,
        image_bytes=content,
        original_filename=original_filename,
        content_type=file.content_type,
    )

    # Save metadata locally for file_id resolution
    meta = {
        "s3_key": result["s3_key"],
        "filename": original_filename,
        "content_type": result["content_type"],
        "file_size_bytes": result["file_size_bytes"],
    }
    with open(os.path.join(_META_DIR, f"{file_id}.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f)

    return {
        "file_id": file_id,
        "filename": original_filename,
        "content_type": result["content_type"],
        "file_size_bytes": result["file_size_bytes"],
    }
