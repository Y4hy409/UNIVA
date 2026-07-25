"""
CLARIUS Backend - Data Importer Service

This service parses CSV and Excel files, maps columns based on configuration,
and loads them into DuckDB in chunks (ADR-005).
"""

import csv
import json
import logging
from pathlib import Path
from typing import Dict, Any, List

from app.infrastructure.database import db_manager
from app.infrastructure.jobs.queue import job_queue
from app.infrastructure.jobs.models import JobStatus

logger = logging.getLogger("clarius.importer")

async def import_csv_handler(job_id: str, payload: Dict[str, Any]) -> None:
    """
    Background job handler to process CSV file imports.
    Payload expectations:
    - file_path: str
    - target_table: str
    - mappings: List[dict] (source_column, target_field, data_type)
    - has_header: bool (default True)
    """
    file_path = Path(payload["file_path"])
    target_table = payload["target_table"]
    mappings = payload["mappings"]
    has_header = payload.get("has_header", True)
    
    if not file_path.exists():
        raise FileNotFoundError(f"Source file {file_path} not found.")

    logger.info(f"Importing CSV {file_path} into table '{target_table}'")
    
    # 1. Parse CSV and build DuckDB commands
    conn = db_manager.get_connection()
    
    # Read mapping lists
    source_cols = [m["source_column"] for m in mappings]
    target_fields = [m["target_field"] for m in mappings]
    
    # Check if table exists, if not, create it
    # We build the CREATE TABLE query based on mapped target fields
    columns_def = []
    for m in mappings:
        field_type = "VARCHAR"
        if m["data_type"] == "float":
            field_type = "DOUBLE"
        elif m["data_type"] == "integer":
            field_type = "INTEGER"
        elif m["data_type"] == "date":
            field_type = "TIMESTAMP"
        columns_def.append(f"{m['target_field']} {field_type}")
        
    conn.execute(f"CREATE TABLE IF NOT EXISTS {target_table} ({', '.join(columns_def)});\n")
    
    # Read CSV rows
    with open(file_path, "r", encoding="utf-8-sig") as f:
        # Determine CSV dialect / delimiter
        dialect = csv.Sniffer().sniff(f.read(1024))
        f.seek(0)
        
        reader = csv.reader(f, dialect)
        header = next(reader) if has_header else None
        
        # Build mapping index dictionary
        col_index = {}
        if header:
            # Strip extra spaces and quotes
            header = [col.strip().strip('"').strip("'") for col in header]
            for s_col in source_cols:
                if s_col in header:
                    col_index[s_col] = header.index(s_col)
                else:
                    # Fallback to column index if named matches fail
                    try:
                        col_index[s_col] = int(s_col)
                    except ValueError:
                        raise ValueError(f"Mapping source column '{s_col}' not found in CSV header: {header}")
        else:
            # If no header, assume source columns are 0-indexed integers
            for s_col in source_cols:
                col_index[s_col] = int(s_col)

        rows_to_insert = []
        total_rows_approx = sum(1 for _ in open(file_path, "r", encoding="utf-8")) - (1 if has_header else 0)
        
        # Re-seek file for reading data
        f.seek(0)
        if has_header:
            next(f)
            
        reader = csv.reader(f, dialect)
        count = 0
        
        for row in reader:
            if not row:
                continue
                
            mapped_row = []
            for m in mappings:
                idx = col_index[m["source_column"]]
                val = row[idx].strip() if idx < len(row) else None
                
                # Cast values
                if val == "" or val is None:
                    mapped_row.append(None)
                elif m["data_type"] == "float":
                    mapped_row.append(float(val))
                elif m["data_type"] == "integer":
                    mapped_row.append(int(val))
                else:
                    mapped_row.append(val)
            
            rows_to_insert.append(mapped_row)
            count += 1
            
            # Batch inserts every 500 rows
            if len(rows_to_insert) >= 500:
                placeholders = ", ".join(["?"] * len(target_fields))
                conn.executemany(
                    f"INSERT INTO {target_table} ({', '.join(target_fields)}) VALUES ({placeholders})",
                    rows_to_insert
                )
                rows_to_insert = []
                # Update progress
                progress = min(0.95, count / total_rows_approx)
                job_queue.update_job_status(
                    job_id, 
                    JobStatus.RUNNING, 
                    progress=progress, 
                    message=f"Imported {count} rows..."
                )
                
        # Final insert
        if rows_to_insert:
            placeholders = ", ".join(["?"] * len(target_fields))
            conn.executemany(
                f"INSERT INTO {target_table} ({', '.join(target_fields)}) VALUES ({placeholders})",
                rows_to_insert
            )
            
        logger.info(f"Imported {count} rows from CSV into {target_table}.")


async def import_excel_handler(job_id: str, payload: Dict[str, Any]) -> None:
    """
    Background job handler to process Excel file (.xlsx) imports.
    """
    file_path = Path(payload["file_path"])
    target_table = payload["target_table"]
    mappings = payload["mappings"]
    sheet_name = payload.get("sheet_name") # Optional specific sheet

    import openpyxl
    
    wb = openpyxl.load_workbook(str(file_path), read_only=True, data_only=True)
    sheet = wb[sheet_name] if sheet_name else wb.active
    
    conn = db_manager.get_connection()
    
    source_cols = [m["source_column"] for m in mappings]
    target_fields = [m["target_field"] for m in mappings]
    
    # Setup tables
    columns_def = []
    for m in mappings:
        field_type = "VARCHAR"
        if m["data_type"] == "float":
            field_type = "DOUBLE"
        elif m["data_type"] == "integer":
            field_type = "INTEGER"
        elif m["data_type"] == "date":
            field_type = "TIMESTAMP"
        columns_def.append(f"{m['target_field']} {field_type}")
        
    conn.execute(f"CREATE TABLE IF NOT EXISTS {target_table} ({', '.join(columns_def)});\n")
    
    rows_iterator = sheet.iter_rows(values_only=True)
    header = next(rows_iterator)
    
    header = [str(col).strip().strip('"').strip("'") if col is not None else "" for col in header]
    
    col_index = {}
    for s_col in source_cols:
        if s_col in header:
            col_index[s_col] = header.index(s_col)
        else:
            try:
                col_index[s_col] = int(s_col)
            except ValueError:
                raise ValueError(f"Mapping source column '{s_col}' not found in Excel header: {header}")
                
    rows_to_insert = []
    count = 0
    
    for row in rows_iterator:
        if not any(row):  # Skip empty rows
            continue
            
        mapped_row = []
        for m in mappings:
            idx = col_index[m["source_column"]]
            val = row[idx] if idx < len(row) else None
            
            # Cast values
            if val == "" or val is None:
                mapped_row.append(None)
            elif m["data_type"] == "float":
                mapped_row.append(float(val))
            elif m["data_type"] == "integer":
                mapped_row.append(int(val))
            else:
                mapped_row.append(str(val))
                
        rows_to_insert.append(mapped_row)
        count += 1
        
        if len(rows_to_insert) >= 500:
            placeholders = ", ".join(["?"] * len(target_fields))
            conn.executemany(
                f"INSERT INTO {target_table} ({', '.join(target_fields)}) VALUES ({placeholders})",
                rows_to_insert
            )
            rows_to_insert = []
            job_queue.update_job_status(
                job_id, 
                JobStatus.RUNNING, 
                progress=0.5,  # Estimate halfway since it's read-only sheet
                message=f"Imported {count} Excel rows..."
            )
            
    if rows_to_insert:
        placeholders = ", ".join(["?"] * len(target_fields))
        conn.executemany(
            f"INSERT INTO {target_table} ({', '.join(target_fields)}) VALUES ({placeholders})",
            rows_to_insert
        )
        
    logger.info(f"Imported {count} rows from Excel into {target_table}.")
