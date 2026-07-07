#!/usr/bin/env python3
"""
Reprocess contracts that are stuck or have incomplete analysis
"""
import sys
import asyncio
import argparse
from database import get_supabase
from contract_processor import process_contract
from logger_config import get_logger
from dotenv import load_dotenv

load_dotenv()
logger = get_logger(__name__)

async def reprocess_stuck_contracts(auto_yes=False):
    """Find and reprocess contracts with incomplete or incorrect risk scores"""
    supabase = get_supabase()

    print("=" * 80)
    print("CONTRACT REPROCESSING TOOL")
    print("=" * 80)

    # Find documents with invalid risk scores
    print("\n📊 Searching for contracts with invalid risk scores...")

    # Query for documents that have mismatched risk_level and risk_score
    # OR have NULL risk scores
    result = supabase.table('contract_analysis')\
        .select('id, document_id, overall_risk_level, risk_score, documents!inner(filename)')\
        .execute()

    all_analyses = result.data
    stuck_docs = []

    for analysis in all_analyses:
        risk_level = analysis.get('overall_risk_level')
        risk_score = analysis.get('risk_score')

        # Check if risk score is NULL or doesn't match the risk level
        needs_reprocess = False
        reason = ""

        if risk_score is None or risk_level is None or risk_level == '':
            needs_reprocess = True
            reason = f"NULL values (level={risk_level}, score={risk_score})"
        elif risk_level == 'high' and risk_score < 50:
            needs_reprocess = True
            reason = f"High risk but score {risk_score} < 50"
        elif risk_level == 'medium' and (risk_score < 20 or risk_score >= 50):
            needs_reprocess = True
            reason = f"Medium risk but score {risk_score} not in range 20-49"
        elif risk_level == 'low' and risk_score >= 20:
            needs_reprocess = True
            reason = f"Low risk but score {risk_score} >= 20"

        if needs_reprocess:
            stuck_docs.append({
                'id': analysis['document_id'],
                'filename': analysis['documents']['filename'],
                'processing_status': 'completed',
                'overall_risk_level': risk_level,
                'risk_score': risk_score,
                'reason': reason
            })

    if not stuck_docs:
        print("✅ No contracts with invalid risk scores found!")
        return

    print(f"📋 Found {len(stuck_docs)} contract(s) with invalid risk scores:")
    for doc in stuck_docs:
        print(f"   - {doc['filename']}")
        print(f"     Current: {doc.get('overall_risk_level', 'N/A')} (score: {doc.get('risk_score', 'N/A')})")
        print(f"     Reason: {doc.get('reason', 'Unknown')}")

    # Confirm with user
    if not auto_yes:
        response = input(f"\n⚠️  Reprocess these {len(stuck_docs)} contract(s)? (y/n): ")
        if response.lower() != 'y':
            print("❌ Cancelled")
            return
    else:
        print(f"\n✅ Auto-proceeding with {len(stuck_docs)} contracts (--yes flag)")

    print("\n🔄 Reprocessing contracts...")
    print("-" * 80)

    success_count = 0
    error_count = 0

    for i, doc in enumerate(stuck_docs, 1):
        doc_id = doc['id']
        filename = doc['filename']

        print(f"\n[{i}/{len(stuck_docs)}] Processing: {filename}")
        print(f"    Document ID: {doc_id}")

        try:
            # Delete existing contract_analysis (whether complete or incomplete)
            print("    🗑️  Cleaning up existing analysis...")
            supabase.table('contract_analysis')\
                .delete()\
                .eq('document_id', doc_id)\
                .execute()

            # Reset document status
            print("    🔄 Resetting document status...")
            supabase.table('documents').update({
                'processing_status': 'processing'
            }).eq('id', doc_id).execute()

            # Process the contract
            print("    ⚙️  Running contract analysis...")
            result = await process_contract(doc_id)

            if result and result.get('overall_risk_level'):
                print(f"    ✅ SUCCESS - Risk Level: {result['overall_risk_level']}")
                print(f"       Confidence: {result.get('confidence_score', 'N/A')}%")
                print(f"       Contract Type: {result.get('contract_type', 'N/A')}")
                success_count += 1
            else:
                print(f"    ⚠️  Analysis completed but missing risk level")
                error_count += 1

        except Exception as e:
            print(f"    ❌ ERROR: {str(e)}")
            logger.error(f"Failed to process {filename}: {e}", exc_info=True)
            error_count += 1

            # Update document with error status
            try:
                error_msg = str(e)[:200]  # Truncate long error messages
                supabase.table('documents').update({
                    'processing_status': 'error',
                    'error_message': error_msg
                }).eq('id', doc_id).execute()
            except Exception as update_error:
                logger.error(f"Failed to update error status: {update_error}")

    # Summary
    print("\n" + "=" * 80)
    print("REPROCESSING SUMMARY")
    print("=" * 80)
    print(f"✅ Successfully processed: {success_count}")
    print(f"❌ Errors: {error_count}")
    print(f"📊 Total: {len(stuck_docs)}")

    if error_count > 0:
        print("\n⚠️  Some contracts failed to process. Check logs for details.")
        print("   You may need to investigate API limits, configuration, or contract content.")

    print("\n✅ Done!")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Reprocess stuck contracts')
    parser.add_argument('--yes', '-y', action='store_true',
                       help='Auto-approve without prompting')
    args = parser.parse_args()

    try:
        asyncio.run(reprocess_stuck_contracts(auto_yes=args.yes))
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
