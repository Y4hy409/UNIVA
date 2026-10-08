"""
CLARIUS Backend - Plugin Host Registry

This module scans directories, validates manifests, dynamically imports entry points,
and manages the active runtime registry of ERP and Data plugins (P2).
"""

import os
import json
import importlib
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Type

from app.plugins.manifest import PluginManifest
from app.plugins.base import IPlugin
from app.infrastructure.licensing import capability_service

logger = logging.getLogger("clarius.plugins.host")


class PluginHost:
    """Manages discovery, manifest checking, and class loading of system plugins."""

    def __init__(self, search_path: Optional[Path] = None):
        self.search_path = search_path or Path(__file__).parent / "erp"
        self.registry: Dict[str, Type[IPlugin]] = {}
        self.manifests: Dict[str, PluginManifest] = {}

    def discover_plugins(self) -> List[PluginManifest]:
        """Scan subfolders in search path for manifest.json and register them."""
        discovered = []
        if not self.search_path.exists():
            return discovered

        # Scan folders inside search_path
        for child in self.search_path.iterdir():
            if child.is_dir():
                manifest_path = child / "manifest.json"
                if manifest_path.exists():
                    try:
                        with manifest_path.open("r", encoding="utf-8") as f:
                            data = json.load(f)
                        manifest = PluginManifest(**data)
                        
                        self.manifests[manifest.plugin_id] = manifest
                        discovered.append(manifest)
                        logger.info(f"Discovered plugin '{manifest.name}' ({manifest.plugin_id})")
                    except Exception as e:
                        logger.error(f"Failed to load manifest at {manifest_path}: {str(e)}")
        return discovered

    def load_plugin(self, plugin_id: str) -> Optional[IPlugin]:
        """Import entry point and construct instance of the target plugin."""
        manifest = self.manifests.get(plugin_id)
        if not manifest:
            logger.error(f"Plugin '{plugin_id}' not discovered in registry.")
            return None

        # Verify licensing capability gating rules
        for cap in manifest.required_capabilities:
            if not capability_service.has_capability(cap):
                logger.warning(f"Plugin '{plugin_id}' loading blocked due to missing capability: {cap}")
                return None

        try:
            # Entry point split, e.g. "app.plugins.erp.erpnext.connector:ERPNextConnector"
            module_path, class_name = manifest.entry_point.split(":")
            module = importlib.import_module(module_path)
            plugin_class = getattr(module, class_name)
            
            instance = plugin_class(manifest=manifest)
            self.registry[plugin_id] = plugin_class
            logger.info(f"Plugin '{plugin_id}' loaded successfully.")
            return instance
        except Exception as e:
            logger.error(f"Failed to dynamically import plugin entry '{manifest.entry_point}': {str(e)}")
            return None

    def get_loaded_plugins(self) -> List[str]:
        """Return IDs of all loaded plugin types."""
        return list(self.registry.keys())


# Centralized host instance
plugin_host = PluginHost()
