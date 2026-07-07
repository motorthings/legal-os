#!/usr/bin/env python3
"""
Upload System Instructions to Supabase Storage

This script uploads local system instruction files to Supabase Storage
to make them persistent and available in production.

Usage:
    python upload_system_instructions.py
    python upload_system_instructions.py --user-id d3ba5354-873a-435a-a36a-853373c4f6e5
    python upload_system_instructions.py --all
"""

import argparse
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from database import get_supabase
from logger_config import get_logger

logger = get_logger(__name__)

SYSTEM_INSTRUCTIONS_DIR = Path(__file__).parent / "system_instructions"
USERS_DIR = SYSTEM_INSTRUCTIONS_DIR / "users"


def upload_file_to_supabase(local_path: Path, storage_path: str) -> bool:
    """
    Upload a file to Supabase Storage.

    Args:
        local_path: Path to local file
        storage_path: Path in Supabase Storage (e.g., "users/user-id.txt")

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        supabase = get_supabase()

        # Read file content
        with open(local_path, 'rb') as f:
            file_content = f.read()

        # Try to update existing file first
        try:
            logger.info(f"   Attempting to update existing file: {storage_path}")
            result = supabase.storage.from_('system-instructions').update(
                storage_path,
                file_content,
                {'content-type': 'text/plain; charset=utf-8'}
            )
            logger.info(f"   ✅ Updated: {storage_path}")
            return True
        except Exception as update_error:
            # If update fails, try upload (file might not exist yet)
            logger.info(f"   File doesn't exist, uploading new: {storage_path}")
            result = supabase.storage.from_('system-instructions').upload(
                storage_path,
                file_content,
                {'content-type': 'text/plain; charset=utf-8'}
            )
            logger.info(f"   ✅ Uploaded: {storage_path}")
            return True

    except Exception as e:
        logger.error(f"   ❌ Failed to upload {storage_path}: {e}")
        return False


def upload_user_instructions(user_id: str) -> bool:
    """Upload system instructions for a specific user."""
    local_file = USERS_DIR / f"{user_id}.txt"

    if not local_file.exists():
        logger.error(f"❌ File not found: {local_file}")
        return False

    logger.info(f"\n📤 Uploading instructions for user: {user_id}")
    logger.info(f"   Local file: {local_file}")

    storage_path = f"users/{user_id}.txt"
    return upload_file_to_supabase(local_file, storage_path)


def upload_all_user_instructions() -> dict:
    """Upload all user-specific system instructions."""
    logger.info("\n📤 Uploading ALL user-specific system instructions...")

    if not USERS_DIR.exists():
        logger.error(f"❌ Users directory not found: {USERS_DIR}")
        return {'success': 0, 'failed': 0}

    user_files = list(USERS_DIR.glob("*.txt"))

    if not user_files:
        logger.warning(f"⚠️  No user instruction files found in {USERS_DIR}")
        return {'success': 0, 'failed': 0}

    logger.info(f"   Found {len(user_files)} user instruction file(s)")

    results = {'success': 0, 'failed': 0}

    for user_file in user_files:
        user_id = user_file.stem  # filename without extension
        if upload_user_instructions(user_id):
            results['success'] += 1
        else:
            results['failed'] += 1

    return results


def main():
    parser = argparse.ArgumentParser(
        description='Upload system instructions to Supabase Storage'
    )
    parser.add_argument(
        '--user-id',
        help='Upload instructions for a specific user ID'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Upload instructions for all users'
    )

    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info("SYSTEM INSTRUCTIONS UPLOAD TO SUPABASE STORAGE")
    logger.info("=" * 80)

    try:
        if args.user_id:
            # Upload for specific user
            success = upload_user_instructions(args.user_id)
            sys.exit(0 if success else 1)

        elif args.all:
            # Upload for all users
            results = upload_all_user_instructions()
            logger.info("\n" + "=" * 80)
            logger.info(f"RESULTS: {results['success']} succeeded, {results['failed']} failed")
            logger.info("=" * 80)
            sys.exit(0 if results['failed'] == 0 else 1)

        else:
            # Default: show usage
            parser.print_help()
            logger.info("\nExamples:")
            logger.info("  python upload_system_instructions.py --all")
            logger.info("  python upload_system_instructions.py --user-id d3ba5354-873a-435a-a36a-853373c4f6e5")
            sys.exit(0)

    except Exception as e:
        logger.error(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
