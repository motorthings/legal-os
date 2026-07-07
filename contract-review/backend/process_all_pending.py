#!/usr/bin/env python3
"""
Process all pending contracts
"""
import asyncio
from database import get_supabase
from contract_processor import process_contract
from logger_config import get_logger
from dotenv import load_dotenv

load_dotenv()
logger = get_logger(__name__)

async def main():
    supabase = get_supabase()

    # Get all pending documents
    result = supabase.table('documents').select('id, filename').eq('processing_status', 'pending').execute()
    pending_docs = result.data

    if not pending_docs:
        print("No pending documents found!")
        return

    print(f"Processing {len(pending_docs)} pending documents...")

    for i, doc in enumerate(pending_docs, 1):
        print(f"\n[{i}/{len(pending_docs)}] Processing: {doc['filename']}")
        try:
            await process_contract(doc['id'])
            print(f"  ✅ Complete")
        except Exception as e:
            print(f"  ❌ Error: {e}")

    print("\n✅ Done processing all pending documents!")

if __name__ == '__main__':
    asyncio.run(main())
