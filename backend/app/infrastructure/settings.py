"""
CLARIUS Backend - Hierarchical Settings Store

This module implements a namespace-based hierarchical settings store (ADR-010)
resolving configuration in order of: User -> Organization -> System -> Defaults.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from uuid import UUID

from app.core.config import settings

SETTINGS_FILE = Path("data/settings.json")

class SettingsStore:
    """Manages hierarchical configuration stored in a local JSON file."""
    
    def __init__(self, file_path: Path = SETTINGS_FILE):
        self.file_path = file_path
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self._load_data()

    def _load_data(self) -> None:
        if self.file_path.exists():
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception:
                self.data = {}
        else:
            self.data = {
                "system": {},
                "organization": {},
                "users": {}
            }
            self._save_data()

    def _save_data(self) -> None:
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            pass # Keep offline robust

    def get_value(self, key: str, user_id: Optional[UUID] = None, default: Any = None) -> Any:
        """
        Get settings value based on precedence hierarchy:
        1. User-specific setting (if user_id provided)
        2. Organization-level setting
        3. System-wide setting
        4. Application-wide default constant
        """
        # 1. User level check
        if user_id:
            user_str = str(user_id)
            user_val = self.data.get("users", {}).get(user_str, {}).get(key)
            if user_val is not None:
                return user_val

        # 2. Org level check
        org_val = self.data.get("organization", {}).get(key)
        if org_val is not None:
            return org_val

        # 3. System level check
        sys_val = self.data.get("system", {}).get(key)
        if sys_val is not None:
            return sys_val

        # 4. Fallback to default
        return default

    def set_system_value(self, key: str, value: Any) -> None:
        """Set a system-wide setting."""
        if "system" not in self.data:
            self.data["system"] = {}
        self.data["system"][key] = value
        self._save_data()

    def set_org_value(self, key: str, value: Any) -> None:
        """Set an organization-level setting."""
        if "organization" not in self.data:
            self.data["organization"] = {}
        self.data["organization"][key] = value
        self._save_data()

    def set_user_value(self, user_id: UUID, key: str, value: Any) -> None:
        """Set a user-specific setting."""
        user_str = str(user_id)
        if "users" not in self.data:
            self.data["users"] = {}
        if user_str not in self.data["users"]:
            self.data["users"][user_str] = {}
        self.data["users"][user_str][key] = value
        self._save_data()


# Global settings store instance
settings_store = SettingsStore()

def get_settings_store() -> SettingsStore:
    """FastAPI dependency."""
    return settings_store
