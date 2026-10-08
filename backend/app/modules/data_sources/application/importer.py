"""
CLARIUS Backend - Data Importer Service

This service parses CSV, Excel, and JSON files, maps columns based on configuration,
and loads them into DuckDB in chunks (ADR-005).
"""

import csv
import json
import re
import logging
from pathlib import Path
from typing import Dict, Any, List

from app.infrastructure.database import db_manager
from app.infrastructure.jobs.queue import job_queue
from app.infrastructure.jobs.models import JobStatus

logger = logging.getLogger("clarius.importer")


def clean_identifier(name: str) -> str:
    """Sanitize table or column name into a safe SQL identifier."""
    clean = re.sub(r'[^a-zA-Z0-9_]', '_', str(name).lower().strip()).strip('_')
    return clean if clean else "col"


async def import_csv_handler(job_id: str, payload: Dict[str, Any]) -> None:
    """
    Background job handler to process CSV file imports.
    """
    file_path = Path(payload["file_path"])
    raw_target_table = payload["target_table"]
    target_table = clean_identifier(raw_target_table)
    mappings = payload.get("mappings", [])
    has_header = payload.get("has_header", True)
    
    if not file_path.exists():
        raise FileNotFoundError(f"Source file {file_path} not found.")

    # Check magic bytes to prevent reading binary Excel files (ZIP b'PK\x03\x04') as raw CSV text
    with open(file_path, "rb") as bf:
        magic = bf.read(4)
    if magic.startswith(b'PK\x03\x04') or magic.startswith(b'\xd0\xcf\x11\xe0') or file_path.suffix.lower() in ('.xlsx', '.xls'):
        logger.info(f"Source file {file_path} is an Excel archive. Redirecting to import_excel_handler.")
        await import_excel_handler(job_id, payload)
        return

    logger.info(f"Importing CSV {file_path} into table '{target_table}'")
    conn = db_manager.get_connection()

    # Primary Ingestion via DuckDB native read_csv_auto (handles unquoted commas, dirty numbers, and all data rows)
    conn.execute(f"DROP TABLE IF EXISTS {target_table};")
    conn.execute(f"CREATE TABLE {target_table} AS SELECT * FROM read_csv_auto('{str(file_path)}', ignore_errors=true, all_varchar=true);")
    count = conn.execute(f"SELECT COUNT(*) FROM {target_table}").fetchone()[0]

    # Clean column headers and apply mapping field renames
    if count > 0:
        info = conn.execute(f"PRAGMA table_info('{target_table}')").fetchall()
        existing_cols = {col[1].lower(): col[1] for col in info}
        
        # Clean current column names into snake_case
        for col_name in list(existing_cols.values()):
            clean_name = clean_identifier(col_name)
            if clean_name != col_name and clean_name:
                try:
                    conn.execute(f'ALTER TABLE {target_table} RENAME COLUMN "{col_name}" TO "{clean_name}";')
                except Exception:
                    pass

        # Apply mapped business fields
        if mappings:
            info_updated = conn.execute(f"PRAGMA table_info('{target_table}')").fetchall()
            current_cols = {col[1].lower(): col[1] for col in info_updated}

            for m in mappings:
                s_col = str(m.get("source_column") or "").strip().replace('\ufeff', '').strip('"').strip("'")
                if not s_col:
                    continue
                t_field = clean_identifier(m.get("target_field") or m.get("suggested_business_field") or s_col)
                s_col_clean = clean_identifier(s_col)

                if s_col_clean.lower() in current_cols:
                    real_col = current_cols[s_col_clean.lower()]
                    if real_col != t_field and t_field:
                        try:
                            conn.execute(f'ALTER TABLE {target_table} RENAME COLUMN "{real_col}" TO "{t_field}";')
                            current_cols[t_field.lower()] = t_field
                        except Exception:
                            pass

    conn.execute("CHECKPOINT;")
    logger.info(f"Successfully imported {count} CSV rows into table '{target_table}'.")

    # Invalidate relationship cache so the next catalog request reflects the new dataset
    try:
        from app.modules.catalog.api.routes import _invalidate_rel_cache
        _invalidate_rel_cache()
    except Exception:
        pass


async def import_excel_handler(job_id: str, payload: Dict[str, Any]) -> None:
    """
    Background job handler to process Excel (.xlsx) file imports.
    """
    file_path = Path(payload["file_path"])
    raw_target_table = payload["target_table"]
    target_table = clean_identifier(raw_target_table)
    mappings = payload.get("mappings", [])
    sheet_name = payload.get("sheet_name")

    import openpyxl
    wb = openpyxl.load_workbook(str(file_path), read_only=True, data_only=True)
    sheet = wb[sheet_name] if sheet_name else wb.active

    conn = db_manager.get_connection()
    rows_iterator = sheet.iter_rows(values_only=True)
    raw_header = next(rows_iterator, None)

    if not raw_header:
        raise ValueError("Excel sheet is empty or missing headers.")

    cleaned_header = [str(col).strip().strip('"').strip("'") if col is not None else "" for col in raw_header]

    if mappings:
        col_specs = []
        col_indices = []
        target_fields = []
        for m in mappings:
            s_col = m.get("source_column")
            t_field = clean_identifier(m.get("target_field") or s_col)
            data_type = str(m.get("data_type", "VARCHAR")).upper()
            if "INTEGER" in data_type or "INT" in data_type:
                sql_type = "BIGINT"
            elif "DECIMAL" in data_type or "FLOAT" in data_type or "DOUBLE" in data_type:
                sql_type = "DOUBLE"
            elif "DATE" in data_type or "TIME" in data_type:
                sql_type = "TIMESTAMP"
            else:
                sql_type = "VARCHAR"

            if s_col in cleaned_header:
                idx = cleaned_header.index(s_col)
            else:
                idx = -1
                for i, h in enumerate(cleaned_header):
                    if h.lower() == str(s_col).lower():
                        idx = i
                        break
                if idx == -1:
                    continue

            col_indices.append(idx)
            target_fields.append(t_field)
            col_specs.append(f"{t_field} {sql_type}")
    else:
        col_indices = list(range(len(cleaned_header)))
        target_fields = [clean_identifier(h) for h in cleaned_header if h]
        col_specs = [f"{tf} VARCHAR" for tf in target_fields]

    if not target_fields:
        col_indices = list(range(len(cleaned_header)))
        target_fields = [clean_identifier(h) for h in cleaned_header if h]
        col_specs = [f"{tf} VARCHAR" for tf in target_fields]

    conn.execute(f"DROP TABLE IF EXISTS {target_table};")
    conn.execute(f"CREATE TABLE {target_table} ({', '.join(col_specs)});")

    rows_to_insert = []
    count = 0

    for row in rows_iterator:
        if not row or not any(c is not None and str(c).strip() != "" for c in row):
            continue

        mapped_row = []
        for idx in col_indices:
            val = row[idx] if idx < len(row) else None
            mapped_row.append(str(val).strip() if val is not None else None)

        rows_to_insert.append(mapped_row)
        count += 1

        if len(rows_to_insert) >= 500:
            placeholders = ", ".join(["?"] * len(target_fields))
            conn.executemany(
                f"INSERT INTO {target_table} ({', '.join(target_fields)}) VALUES ({placeholders})",
                rows_to_insert
            )
            rows_to_insert = []

    if rows_to_insert:
        placeholders = ", ".join(["?"] * len(target_fields))
        conn.executemany(
            f"INSERT INTO {target_table} ({', '.join(target_fields)}) VALUES ({placeholders})",
            rows_to_insert
        )

    conn.execute("CHECKPOINT;")
    logger.info(f"Successfully imported {count} Excel rows into table '{target_table}'.")


async def import_json_handler(job_id: str, payload: Dict[str, Any]) -> None:
    """
    Background job handler to process JSON file imports.
    """
    file_path = Path(payload["file_path"])
    raw_target_table = payload["target_table"]
    target_table = clean_identifier(raw_target_table)

    if not file_path.exists():
        raise FileNotFoundError(f"Source file {file_path} not found.")

    conn = db_manager.get_connection()
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list) or len(data) == 0:
        raise ValueError("JSON file must contain a non-empty array of objects.")

    headers = list(data[0].keys())
    target_fields = [clean_identifier(h) for h in headers]
    col_specs = [f"{tf} VARCHAR" for tf in target_fields]

    conn.execute(f"DROP TABLE IF EXISTS {target_table};")
    conn.execute(f"CREATE TABLE {target_table} ({', '.join(col_specs)});")

    rows_to_insert = []
    for item in data:
        row = [str(item.get(h)) if item.get(h) is not None else None for h in headers]
        rows_to_insert.append(row)

    placeholders = ", ".join(["?"] * len(target_fields))
    conn.executemany(
        f"INSERT INTO {target_table} ({', '.join(target_fields)}) VALUES ({placeholders})",
        rows_to_insert
    )

    conn.execute("CHECKPOINT;")
    logger.info(f"Successfully imported {len(rows_to_insert)} JSON records into table '{target_table}'.")

