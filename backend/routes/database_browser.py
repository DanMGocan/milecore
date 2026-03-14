import re

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.database import (
    execute_query,
    get_table_rows,
    get_table_schema,
    get_tables,
)

router = APIRouter(prefix="/tables")


@router.get("/download")
async def download_database():
    from backend.config import DATABASE_PATH
    return FileResponse(DATABASE_PATH, filename="milecore.db", media_type="application/octet-stream")


def _validate_name(name: str) -> str:
    if not re.match(r"^\w+$", name):
        raise HTTPException(status_code=400, detail="Invalid name")
    return name


# --- Table operations ---


class CreateTableRequest(BaseModel):
    name: str
    columns: list[dict]  # [{"name": "col1", "type": "TEXT", "notnull": False, "default": None}]


class AddColumnRequest(BaseModel):
    name: str
    type: str = "TEXT"
    default: str | None = None


class InsertRowRequest(BaseModel):
    data: dict


@router.get("")
async def list_tables():
    return {"tables": get_tables()}


@router.post("")
async def create_table(req: CreateTableRequest):
    name = _validate_name(req.name)
    if not req.columns:
        raise HTTPException(status_code=400, detail="At least one column is required")

    col_defs = []
    for col in req.columns:
        col_name = _validate_name(col["name"])
        col_type = col.get("type", "TEXT")
        parts = [col_name, col_type]
        if col.get("notnull"):
            parts.append("NOT NULL")
        if col.get("default") is not None:
            parts.append(f"DEFAULT {col['default']!r}")
        col_defs.append(" ".join(parts))

    col_defs.insert(0, "id INTEGER PRIMARY KEY")
    sql = f"CREATE TABLE {name} ({', '.join(col_defs)})"
    result = execute_query(sql)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"message": f"Table '{name}' created", "sql": sql}


@router.delete("/{table_name}")
async def drop_table(table_name: str):
    name = _validate_name(table_name)
    result = execute_query(f"DROP TABLE IF EXISTS {name}")
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"message": f"Table '{name}' dropped"}


# --- Schema operations ---


@router.get("/{table_name}/schema")
async def table_schema(table_name: str):
    name = _validate_name(table_name)
    schema = get_table_schema(name)
    if not schema:
        raise HTTPException(status_code=404, detail="Table not found")
    return {"table": name, "columns": schema}


@router.post("/{table_name}/columns")
async def add_column(table_name: str, req: AddColumnRequest):
    table = _validate_name(table_name)
    col = _validate_name(req.name)
    sql = f"ALTER TABLE {table} ADD COLUMN {col} {req.type}"
    if req.default is not None:
        sql += f" DEFAULT {req.default!r}"
    result = execute_query(sql)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"message": f"Column '{col}' added to '{table}'"}


# --- Row operations ---


@router.get("/{table_name}/rows")
async def table_rows(
    table_name: str,
    limit: int = Query(default=50, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    name = _validate_name(table_name)
    result = get_table_rows(name, limit, offset)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/{table_name}/rows")
async def insert_row(table_name: str, req: InsertRowRequest):
    name = _validate_name(table_name)
    if not req.data:
        raise HTTPException(status_code=400, detail="No data provided")

    columns = ", ".join(req.data.keys())
    placeholders = ", ".join(["?"] * len(req.data))
    values = list(req.data.values())

    sql = f"INSERT INTO {name} ({columns}) VALUES ({placeholders})"
    result = execute_query(sql, values)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"message": "Row inserted", "id": result.get("lastrowid")}


@router.delete("/{table_name}/rows/{row_id}")
async def delete_row(table_name: str, row_id: int):
    name = _validate_name(table_name)
    result = execute_query(f"DELETE FROM {name} WHERE rowid = ?", [row_id])
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    if result.get("rowcount", 0) == 0:
        raise HTTPException(status_code=404, detail="Row not found")
    return {"message": f"Row {row_id} deleted from '{name}'"}
