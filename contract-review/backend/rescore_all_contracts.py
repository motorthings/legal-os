#!/usr/bin/env python3
"""
Rescore ALL contracts with the updated risk scoring algorithm
This doesn't re-analyze with Claude, just recalculates risk_score and risk_level from existing flags
"""
import sys
from database import get_supabase
from contract_processor import calculate_risk_score, determine_risk_level
from logger_config import get_logger
from dotenv import load_dotenv

load_dotenv()
logger = get_logger(__name__)

def rescore_all_contracts():
    """Recalculate risk scores for all contracts without re-analyzing"""
    supabase = get_supabase()

    print("=" * 80)
    print("CONTRACT RESCORING TOOL")
    print("=" * 80)
    print("\nRecalculating risk scores using new algorithm...")
    print("NOTE: This updates scores based on existing flags, no Claude API calls needed\n")

    # Get all contracts with analysis
    result = supabase.table('contract_analysis')\
        .select('id, document_id, red_flags, yellow_flags, documents!inner(filename)')\
        .execute()

    contracts = result.data
    if not contracts:
        print("✅ No contracts found!")
        return

    print(f"📋 Found {len(contracts)} contract(s) to rescore\n")

    success_count = 0
    error_count = 0

    for i, contract in enumerate(contracts, 1):
        filename = contract['documents']['filename']
        analysis_id = contract['id']

        print(f"[{i}/{len(contracts)}] Rescoring: {filename}")

        try:
            # Reconstruct analysis_result format for calculate_risk_score
            analysis_result = {
                'risk_assessment': {
                    'red_flags': contract.get('red_flags', []) or [],
                    'yellow_flags': contract.get('yellow_flags', []) or []
                }
            }

            # Calculate new risk score
            risk_score = calculate_risk_score(analysis_result)
            red_flags = analysis_result['risk_assessment']['red_flags']
            overall_risk_level = determine_risk_level(risk_score, red_flags)

            # Update database
            supabase.table('contract_analysis').update({
                'risk_score': risk_score,
                'overall_risk_level': overall_risk_level
            }).eq('id', analysis_id).execute()

            print(f"  ✅ Updated: {overall_risk_level} ({risk_score})")
            success_count += 1

        except Exception as e:
            print(f"  ❌ ERROR: {str(e)}")
            logger.error(f"Failed to rescore {filename}: {e}", exc_info=True)
            error_count += 1

    # Summary
    print("\n" + "=" * 80)
    print("RESCORING SUMMARY")
    print("=" * 80)
    print(f"✅ Successfully rescored: {success_count}")
    print(f"❌ Errors: {error_count}")
    print(f"📊 Total: {len(contracts)}")
    print("\n✅ Done!")

if __name__ == "__main__":
    try:
        rescore_all_contracts()
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
