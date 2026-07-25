"""
CLARIUS Backend - Data Sources Domain Models

This module defines models for source database structures, mappings, and schemas (ADR-005).
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from enum import Enum

class TargetCDMTable(str, Enum):
    SALES = "sales"
    INVENTORY = "inventory"
    PURCHASES = "purchases"
    CUSTOMERS = "customers"
    SUPPLIERS = "suppliers"


class ColumnMapping(BaseModel):
    """Maps a raw source column (e.g. from CSV) to a target CDM field."""
    source_column: str
    target_field: str
    data_type: str = "string"  # string, float, integer, date


class SchemaMapping(BaseModel):
    """Defines complete mappings for a file to a CDM target table."""
    data_source_id: str
    target_table: TargetCDMTable
    mappings: List[ColumnMapping]
    has_header: bool = True
