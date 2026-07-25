"""
CLARIUS Backend - Plugin Manifest Validation

This module validates manifests specifying metadata and entries (P2).
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class PluginManifest(BaseModel):
    """Pydantic model representing plugin manifests."""
    plugin_id: str = Field(..., description="Unique slug identifying the plugin")
    name: str = Field(..., description="Human readable plugin name")
    category: str = Field(..., description="Category, e.g. erp, data, ai, automation, exports")
    version: str = Field("1.0.0", description="Plugin version string")
    plugin_api_version: int = Field(1, description="API version target")
    min_clarius_version: str = Field("1.0.0", description="Minimum Clarius host platform version")
    required_capabilities: List[str] = Field(default_factory=list, description="Licensing capability gating rules")
    entry_point: str = Field(..., description="Module import path to connector class")
    description: Optional[str] = Field(None, description="Optional brief description")
