#!/usr/bin/env python3
"""
Seed system instructions from XML files into the database
"""
import os
from database import get_supabase

# Contract types and their corresponding XML files
CONTRACT_TYPES = {
    'vendor': 'VENDOR_CONTRACT_SYSTEM_INSTRUCTIONS.xml',
    'customer': 'CUSTOMER_CONTRACT_SYSTEM_INSTRUCTIONS.xml',
    'employment': 'EMPLOYMENT_CONTRACT_SYSTEM_INSTRUCTIONS.xml',
    'dpa': 'DPA_CONTRACT_SYSTEM_INSTRUCTIONS.xml',
    'general': 'GENERAL_CONTRACT_SYSTEM_INSTRUCTIONS.xml',
    'other': 'OTHER_CONTRACT_SYSTEM_INSTRUCTIONS.xml'
}

def seed_instructions():
    """Load XML files and insert into database"""
    supabase = get_supabase()

    for contract_type, filename in CONTRACT_TYPES.items():
        filepath = os.path.join('system_instructions', filename)

        if not os.path.exists(filepath):
            print(f"⚠️  Warning: {filepath} not found, skipping...")
            continue

        print(f"📄 Reading {filepath}...")
        with open(filepath, 'r') as f:
            instructions = f.read()

        print(f"💾 Upserting {contract_type} instructions to database...")
        try:
            result = supabase.table('contract_type_instructions').upsert({
                'contract_type': contract_type,
                'instructions': instructions
            }, on_conflict='contract_type').execute()

            print(f"✅ Successfully seeded {contract_type} instructions ({len(instructions)} characters)")
        except Exception as e:
            print(f"❌ Error seeding {contract_type}: {str(e)}")

    print("\n✅ Seeding complete!")

if __name__ == '__main__':
    seed_instructions()
