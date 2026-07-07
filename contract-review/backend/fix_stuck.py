#!/usr/bin/env python3
"""Fix the 3 stuck contracts"""
import asyncio
from dotenv import load_dotenv
from contract_processor import process_contract
from logger_config import get_logger

load_dotenv()
logger = get_logger(__name__)

STUCK_IDS = [
    '9a935ecc-18de-43eb-8b4d-6618ff76507a',  # employment_offer_compliant.txt
    'ebf9ea26-94e9-48b3-8578-e7b3813c97d8',  # general_jv_medium.txt
    '5e36cceb-9c00-43a0-abf2-9a2f6b6e6bac',  # general_sow_medium.txt
]

async def main():
    print("Processing 3 stuck contracts...\n")

    for i, doc_id in enumerate(STUCK_IDS, 1):
        print(f"[{i}/3] Processing {doc_id}...")
        try:
            await process_contract(doc_id)
            print(f"  ✅ Complete\n")
        except Exception as e:
            print(f"  ❌ Error: {e}\n")
            logger.error(f"Failed to process {doc_id}: {e}", exc_info=True)

    print("✅ Done!")

if __name__ == '__main__':
    asyncio.run(main())
