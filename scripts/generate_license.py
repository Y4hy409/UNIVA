"""
CLARIUS / UNIVA Offline License Key Generator

This script generates valid, cryptographically signed offline .lic license files
for the CLARIUS platform using Ed25519 signatures.

Usage:
    python scripts/generate_license.py --edition univa --org "Acme Corp" --users 50 --branches 5 --days 365 --output acme.lic
"""

import argparse
import base64
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import ed25519

# Embedded private key matching PUBLIC_KEY_HEX in app/infrastructure/licensing.py
PRIVATE_KEY_HEX = "5c8f8ab692e2a8684617a233b664d509f6b9868e2f0727dc00966a935fa7c062"


def generate_license(
    edition: str = "univa",
    org_name: str = "Enterprise Client",
    max_users: int = 50,
    max_branches: int = 5,
    valid_days: int = 365,
    strictness: str = "none"
) -> str:
    """Generate a signed Base64 Ed25519 license key payload."""
    private_key = ed25519.Ed25519PrivateKey.from_private_bytes(bytes.fromhex(PRIVATE_KEY_HEX))
    
    expires_at = (datetime.now(timezone.utc) + timedelta(days=valid_days)).isoformat()
    
    payload = {
        "edition": edition.lower(),
        "expires_at": expires_at,
        "grace_days": 14,
        "organization": {
            "name": org_name,
            "max_users": max_users,
            "max_branches": max_branches
        },
        "deployment": {
            "fingerprint_strictness": strictness
        },
        "capabilities": [
            f"{edition.lower()}.*"
        ]
    }
    
    payload_json = json.dumps(payload, indent=None)
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode("utf-8")).decode("utf-8").rstrip("=")
    
    # Sign payload
    signature = private_key.sign(payload_json.encode("utf-8"))
    sig_b64 = base64.urlsafe_b64encode(signature).decode("utf-8").rstrip("=")
    
    return f"CLARIUS-LICENSE-v1\n{payload_b64}\n{sig_b64}"


def main():
    parser = argparse.ArgumentParser(description="Generate CLARIUS / UNIVA Cryptographic Offline License Key (.lic)")
    parser.add_argument("--edition", choices=["clarius", "clarius_copilot", "univa"], default="univa", help="Product Edition")
    parser.add_argument("--org", default="Default Enterprise", help="Organization Name")
    parser.add_argument("--users", type=int, default=50, help="Maximum Allowed User Accounts")
    parser.add_argument("--branches", type=int, default=5, help="Maximum Allowed Branch Nodes")
    parser.add_argument("--days", type=int, default=365, help="License Validity (Days)")
    parser.add_argument("--output", help="Output file path (e.g. client.lic)")
    
    args = parser.parse_args()
    
    license_key = generate_license(
        edition=args.edition,
        org_name=args.org,
        max_users=args.users,
        max_branches=args.branches,
        valid_days=args.days
    )
    
    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(license_key, encoding="utf-8")
        print(f"[SUCCESS] Generated {args.edition.upper()} license key for '{args.org}'!")
        print(f"[FILE] Saved to: {out_path.resolve()}")
    else:
        print("\n--- BEGIN CLARIUS LICENSE KEY ---")
        print(license_key)
        print("--- END CLARIUS LICENSE KEY ---\n")


if __name__ == "__main__":
    main()

