#!/usr/bin/env python3
"""
Script to update contract-type system instructions in the database.
Reads XML files and pushes them to the database via the API.
"""

import os
import requests
from pathlib import Path

# Configuration
API_BASE_URL = "http://localhost:8000"
INSTRUCTIONS_DIR = Path("system_instructions")

# Test admin token (from test setup)
ADMIN_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIwMDAwMDAwMC0wMDAwLTAwMDAtMDAwMC0wMDAwMDAwMDAwMDEiLCJlbWFpbCI6InRlc3RAZXhhbXBsZS5jb20iLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwicm9sZSI6ImF1dGhlbnRpY2F0ZWQiLCJpYXQiOjE3NjQ5ODIwMTIsImV4cCI6MTc2NTA2ODQxMn0.1QgNHfXFeLsnMfktAhbVVXmOappC-03MmcMRrjA456o"

# Contract types to update
CONTRACT_TYPES = ["vendor", "customer", "employment", "dpa", "general", "other"]

def update_contract_type_instructions(contract_type: str) -> bool:
    """Update instructions for a specific contract type."""

    # Construct file path
    filename = f"{contract_type.upper()}_CONTRACT_SYSTEM_INSTRUCTIONS.xml"
    filepath = INSTRUCTIONS_DIR / filename

    if not filepath.exists():
        print(f"❌ File not found: {filepath}")
        return False

    # Read XML content
    with open(filepath, 'r', encoding='utf-8') as f:
        instructions = f.read()

    # Prepare API request
    url = f"{API_BASE_URL}/api/system-instructions/contract-types/{contract_type}"
    headers = {
        "Authorization": f"Bearer {ADMIN_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "instructions": instructions
    }

    # Send request
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()

        data = response.json()
        print(f"✅ {contract_type.upper()}: Updated successfully")
        print(f"   Version: {data.get('version', 'unknown')}")
        print(f"   Updated: {data.get('updated_at', 'unknown')}")
        return True

    except requests.exceptions.RequestException as e:
        print(f"❌ {contract_type.upper()}: Failed to update")
        print(f"   Error: {e}")
        if hasattr(e.response, 'text'):
            print(f"   Response: {e.response.text}")
        return False

def main():
    """Main function to update all contract type instructions."""
    print("=" * 60)
    print("Updating Contract-Type System Instructions")
    print("=" * 60)
    print()

    success_count = 0
    fail_count = 0

    for contract_type in CONTRACT_TYPES:
        success = update_contract_type_instructions(contract_type)
        if success:
            success_count += 1
        else:
            fail_count += 1
        print()

    print("=" * 60)
    print(f"Summary: {success_count} succeeded, {fail_count} failed")
    print("=" * 60)

if __name__ == "__main__":
    main()
