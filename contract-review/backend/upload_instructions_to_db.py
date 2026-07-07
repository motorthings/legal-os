#!/usr/bin/env python3
"""
Upload updated system instructions to Supabase database
"""

import os
from pathlib import Path
from database import get_supabase

def upload_instructions():
    """Upload all contract type instructions to database"""
    supabase = get_supabase()

    contract_types = {
        'vendor': 'VENDOR_CONTRACT_SYSTEM_INSTRUCTIONS.xml',
        'customer': 'CUSTOMER_CONTRACT_SYSTEM_INSTRUCTIONS.xml',
        'employment': 'EMPLOYMENT_CONTRACT_SYSTEM_INSTRUCTIONS.xml',
        'dpa': 'DPA_CONTRACT_SYSTEM_INSTRUCTIONS.xml',
        'general': 'GENERAL_CONTRACT_SYSTEM_INSTRUCTIONS.xml',
        'other': 'OTHER_CONTRACT_SYSTEM_INSTRUCTIONS.xml',
    }

    instructions_dir = Path('system_instructions')

    for contract_type, filename in contract_types.items():
        file_path = instructions_dir / filename

        if not file_path.exists():
            print(f"❌ File not found: {filename}")
            continue

        # Read the XML content
        instructions_content = file_path.read_text()

        # Update in database
        try:
            result = supabase.table('contract_type_instructions')\
                .upsert({
                    'contract_type': contract_type,
                    'instructions': instructions_content,
                    'updated_at': 'now()'
                }, on_conflict='contract_type')\
                .execute()

            print(f"✓ Updated {contract_type} instructions (version 1.2.0)")
        except Exception as e:
            print(f"❌ Failed to update {contract_type}: {e}")

    print("\n✓ All instructions uploaded to database")

if __name__ == "__main__":
    upload_instructions()
