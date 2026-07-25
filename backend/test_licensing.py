"""
CLARIUS Backend - Licensing Verification Test Suite

This module runs comprehensive tests on the offline licensing checks,
validating signature parsing, expiration, capabilities, and fingerprint matches.
"""

import sys
import json
import base64
import unittest
from pathlib import Path
from datetime import datetime, timezone, timedelta
from cryptography.hazmat.primitives.asymmetric import ed25519

# Add app to python path
sys.path.insert(0, str(Path(__file__).parent))

from app.infrastructure.licensing import (
    CapabilityService, LicenseStatus, get_hardware_fingerprint
)

# Test private key hex (matching public key hex in licensing.py)
PRIVATE_KEY_HEX = "5c8f8ab692e2a8684617a233b664d509f6b9868e2f0727dc00966a935fa7c062"


class TestLicensing(unittest.TestCase):

    def setUp(self):
        self.test_license_path = Path("data/test_license.lic")
        self.test_license_path.parent.mkdir(parents=True, exist_ok=True)
        self.private_key = ed25519.Ed25519PrivateKey.from_private_bytes(
            bytes.fromhex(PRIVATE_KEY_HEX)
        )

    def _create_signed_license(self, payload: dict) -> str:
        """Helper to serialize, encode, and sign a license file payload."""
        payload_json = json.dumps(payload)
        payload_b64 = base64.urlsafe_b64encode(payload_json.encode('utf-8')).decode('utf-8').rstrip("=")
        
        # Sign payload
        signature = self.private_key.sign(payload_json.encode('utf-8'))
        sig_b64 = base64.urlsafe_b64encode(signature).decode('utf-8').rstrip("=")
        
        return f"CLARIUS-LICENSE-v1\n{payload_b64}\n{sig_b64}"

    def test_valid_clarius_license(self):
        expiry = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
        payload = {
            "edition": "clarius",
            "expires_at": expiry,
            "organization": {"max_users": 5, "max_branches": 1},
            "deployment": {"fingerprint_strictness": "none"}
        }
        
        license_str = self._create_signed_license(payload)
        self.test_license_path.write_text(license_str, encoding="utf-8")
        
        service = CapabilityService(self.test_license_path)
        self.assertEqual(service.get_license_status(), LicenseStatus.VALID)
        self.assertTrue(service.has_capability("clarius.nl_query"))
        self.assertFalse(service.has_capability("copilot.predictive_analytics"))

    def test_valid_copilot_license(self):
        expiry = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
        payload = {
            "edition": "clarius_copilot",
            "expires_at": expiry,
            "organization": {"max_users": 10},
            "deployment": {"fingerprint_strictness": "none"}
        }
        
        license_str = self._create_signed_license(payload)
        self.test_license_path.write_text(license_str, encoding="utf-8")
        
        service = CapabilityService(self.test_license_path)
        self.assertEqual(service.get_license_status(), LicenseStatus.VALID)
        self.assertTrue(service.has_capability("clarius.nl_query"))
        self.assertTrue(service.has_capability("copilot.predictive_analytics"))
        self.assertFalse(service.has_capability("univa.workflow_automation"))

    def test_expired_license(self):
        # 1 day ago expiration
        expiry = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        payload = {
            "edition": "clarius",
            "expires_at": expiry,
            "grace_days": 0,
            "deployment": {"fingerprint_strictness": "none"}
        }
        
        license_str = self._create_signed_license(payload)
        self.test_license_path.write_text(license_str, encoding="utf-8")
        
        service = CapabilityService(self.test_license_path)
        self.assertEqual(service.get_license_status(), LicenseStatus.EXPIRED)
        self.assertFalse(service.has_capability("clarius.nl_query"))

    def test_grace_period_license(self):
        # 1 day ago expiration, but 7 grace days
        expiry = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        payload = {
            "edition": "clarius",
            "expires_at": expiry,
            "grace_days": 7,
            "deployment": {"fingerprint_strictness": "none"}
        }
        
        license_str = self._create_signed_license(payload)
        self.test_license_path.write_text(license_str, encoding="utf-8")
        
        service = CapabilityService(self.test_license_path)
        self.assertEqual(service.get_license_status(), LicenseStatus.GRACE_PERIOD)
        self.assertTrue(service.has_capability("clarius.nl_query"))

    def test_invalid_signature_tampered(self):
        expiry = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
        payload = {
            "edition": "clarius",
            "expires_at": expiry,
            "deployment": {"fingerprint_strictness": "none"}
        }
        
        license_str = self._create_signed_license(payload)
        # Tamper payload
        lines = license_str.splitlines()
        lines[1] = lines[1] + "tamper"
        tampered_str = "\n".join(lines)
        
        self.test_license_path.write_text(tampered_str, encoding="utf-8")
        
        service = CapabilityService(self.test_license_path)
        self.assertEqual(service.get_license_status(), LicenseStatus.INVALID_SIGNATURE)
        self.assertFalse(service.has_capability("clarius.nl_query"))

    def test_hardware_fingerprint_mismatch(self):
        expiry = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
        payload = {
            "edition": "clarius",
            "expires_at": expiry,
            "deployment": {
                "fingerprint_strictness": "strict",
                "hardware_fingerprint": "wrong_hardware_hash_value"
            }
        }
        
        license_str = self._create_signed_license(payload)
        self.test_license_path.write_text(license_str, encoding="utf-8")
        
        service = CapabilityService(self.test_license_path)
        self.assertEqual(service.get_license_status(), LicenseStatus.INVALID_HARDWARE)
        self.assertFalse(service.has_capability("clarius.nl_query"))

    def test_hardware_fingerprint_match(self):
        fp = get_hardware_fingerprint()
        expiry = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
        payload = {
            "edition": "clarius",
            "expires_at": expiry,
            "deployment": {
                "fingerprint_strictness": "strict",
                "hardware_fingerprint": fp
            }
        }
        
        license_str = self._create_signed_license(payload)
        self.test_license_path.write_text(license_str, encoding="utf-8")
        
        service = CapabilityService(self.test_license_path)
        self.assertEqual(service.get_license_status(), LicenseStatus.VALID)
        self.assertTrue(service.has_capability("clarius.nl_query"))

    def tearDown(self):
        if self.test_license_path.exists():
            self.test_license_path.unlink()


if __name__ == '__main__':
    unittest.main()
