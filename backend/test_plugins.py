"""
CLARIUS Backend - Plugin Host and Connectors Test Suite

This suite verifies manifest parsing, dynamic loading, capability gates,
and data sync operations for all 4 ERP connectors (P2).
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

# Add app to python path
sys.path.insert(0, str(Path(__file__).parent))

from app.plugins.host import PluginHost
from app.plugins.base import ConnectionResult, SourceSchema, SyncResult

class TestPluginArchitecture(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        # Configure search path to the core plugins/erp subfolder
        self.search_path = Path(__file__).parent / "app" / "plugins" / "erp"
        self.host = PluginHost(search_path=self.search_path)

    @patch("app.infrastructure.licensing.CapabilityService.has_capability", return_value=True)
    def test_plugin_discovery(self, mock_cap):
        manifests = self.host.discover_plugins()
        discovered_ids = [m.plugin_id for m in manifests]
        
        self.assertIn("erpnext", discovered_ids)
        self.assertIn("odoo", discovered_ids)
        self.assertIn("tally", discovered_ids)
        self.assertIn("busy", discovered_ids)
        self.assertIn("zoho", discovered_ids)

    @patch("app.infrastructure.licensing.CapabilityService.has_capability", return_value=True)
    async def test_plugin_loading_and_execution(self, mock_cap):
        self.host.discover_plugins()
        
        # 1. Test ERPNext Load & Sync
        erpnext = self.host.load_plugin("erpnext")
        self.assertIsNotNone(erpnext)
        conn_res = await erpnext.test_connection({"url": "http://erpnext.local"})
        self.assertTrue(conn_res.success)
        schema = await erpnext.discover_schema({})
        self.assertIn("customers", schema.tables)
        sync_res = await erpnext.sync_entity("customers", {})
        self.assertTrue(sync_res.success)
        self.assertEqual(sync_res.records_synced, 12)

        # 2. Test Odoo Load & Sync
        odoo = self.host.load_plugin("odoo")
        self.assertIsNotNone(odoo)
        conn_res_odoo = await odoo.test_connection({"database": "db", "username": "user"})
        self.assertTrue(conn_res_odoo.success)
        schema_odoo = await odoo.discover_schema({})
        self.assertIn("sale_order", schema_odoo.tables)
        sync_res_odoo = await odoo.sync_entity("sale_order", {})
        self.assertTrue(sync_res_odoo.success)
        self.assertEqual(sync_res_odoo.records_synced, 45)

        # 3. Test Tally Load & Sync
        tally = self.host.load_plugin("tally")
        self.assertIsNotNone(tally)
        conn_res_tally = await tally.test_connection({"port": "9000"})
        self.assertTrue(conn_res_tally.success)
        schema_tally = await tally.discover_schema({})
        self.assertIn("vouchers", schema_tally.tables)
        sync_res_tally = await tally.sync_entity("vouchers", {})
        self.assertTrue(sync_res_tally.success)
        self.assertEqual(sync_res_tally.records_synced, 150)

        # 4. Test Busy Load & Sync
        busy = self.host.load_plugin("busy")
        self.assertIsNotNone(busy)
        conn_res_busy = await busy.test_connection({"connection_string": "sqlite://"})
        self.assertTrue(conn_res_busy.success)
        schema_busy = await busy.discover_schema({})
        self.assertIn("accounts", schema_busy.tables)
        sync_res_busy = await busy.sync_entity("accounts", {})
        self.assertTrue(sync_res_busy.success)
        self.assertEqual(sync_res_busy.records_synced, 88)

        # 5. Test Zoho Books Load & Sync
        zoho = self.host.load_plugin("zoho")
        self.assertIsNotNone(zoho)
        conn_res_zoho = await zoho.test_connection({"organization_id": "123", "client_id": "id", "client_secret": "sec"})
        self.assertTrue(conn_res_zoho.success)
        schema_zoho = await zoho.discover_schema({})
        self.assertIn("invoices", schema_zoho.tables)
        sync_res_zoho = await zoho.sync_entity("invoices", {})
        self.assertTrue(sync_res_zoho.success)
        self.assertEqual(sync_res_zoho.records_synced, 142)

    @patch("app.infrastructure.licensing.CapabilityService.has_capability", return_value=False)
    def test_capability_gating_blocks_load(self, mock_cap):
        self.host.discover_plugins()
        # Loading should return None when license is insufficient
        erpnext = self.host.load_plugin("erpnext")
        self.assertIsNone(erpnext)


if __name__ == '__main__':
    unittest.main()
