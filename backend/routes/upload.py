import csv
import io

from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.database import execute_query, get_tables

router = APIRouter()


@router.post("/upload")
async def upload_csv(file: UploadFile = File(...), table_name: str | None = None):
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
    existing = get_tables()
    if table_name not in existing:
        columns = rows[0].keys()
        col_defs = ", ".join([f'"{col}" TEXT' for col in columns])
        create_sql = f'CREATE TABLE {table_name} (id INTEGER PRIMARY KEY, {col_defs})'
        result = execute_query(create_sql)
        if "error" in result:
            raise HTTPException(status_code=400, detail=f"Failed to create table: {result['error']}")

    # Insert rows
    inserted = 0
    errors = []
    for i, row in enumerate(rows):
        columns = ", ".join([f'"{k}"' for k in row.keys()])
        placeholders = ", ".join(["?"] * len(row))
        values = list(row.values())
        sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
        result = execute_query(sql, values)
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
