from logger_config import get_logger
logger = get_logger(__name__)

"""
Google Drive Automatic Sync Scheduler

This module provides background job scheduling for automatic Google Drive syncs.
It uses APScheduler to periodically check for users with due syncs and executes them.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from database import get_supabase
from services.google_drive_sync import sync_folder
from services.oauth_crypto import decrypt_token

# Get centralized Supabase client
supabase = get_supabase()

# Global scheduler instance
scheduler: Optional[BackgroundScheduler] = None


def calculate_next_sync_time(frequency: str) -> datetime:
    """
    Calculate the next sync time based on frequency.

    Args:
        frequency: 'daily', 'weekly', or 'monthly'

    Returns:
        datetime: Next scheduled sync time
    """
    now = datetime.now(timezone.utc)

    if frequency == 'daily':
        return now + timedelta(days=1)
    elif frequency == 'weekly':
        return now + timedelta(weeks=1)
    elif frequency == 'monthly':
        return now + timedelta(days=30)
    else:
        return now  # Fallback


def process_automatic_syncs():
    """
    Main job function that checks for and executes due syncs.
    Runs periodically via APScheduler.
    """
    try:
        logger.info(f"\n{'='*60}")
        logger.info(f"🔄 Automatic Sync Job Started: {datetime.now(timezone.utc).isoformat()}")
        logger.info(f"{'='*60}")

        # Query for users with due syncs
        now = datetime.now(timezone.utc)
        result = supabase.table('google_drive_tokens')\
            .select('id, user_id, sync_frequency, next_sync_scheduled, default_folder_id, default_folder_name, access_token_encrypted, refresh_token_encrypted, token_expires_at')\
            .eq('is_active', True)\
            .neq('sync_frequency', 'manual')\
            .lte('next_sync_scheduled', now.isoformat())\
            .execute()

        users_to_sync = result.data

        if not users_to_sync:
            print("   ℹ️  No syncs due at this time")
            logger.info(f"{'='*60}\n")
            return

        logger.info(f"   📋 Found {len(users_to_sync)} user(s) with due syncs")

        # Process each user
        for user_token in users_to_sync:
            try:
                user_id = user_token['user_id']
                folder_id = user_token.get('default_folder_id')
                folder_name = user_token.get('default_folder_name', 'My Drive')
                frequency = user_token['sync_frequency']

                logger.info(f"\n   👤 Processing sync for user {user_id}")
                logger.info(f"      📁 Folder: {folder_name} ({folder_id or 'root'})")
                logger.info(f"      📅 Frequency: {frequency}")

                # Execute sync (sync_folder handles token retrieval internally)
                sync_result = sync_folder(
                    user_id=user_id,
                    folder_id=folder_id,
                    folder_name=folder_name
                )

                # Calculate next sync time
                next_sync = calculate_next_sync_time(frequency)

                # Update database with results
                supabase.table('google_drive_tokens')\
                    .update({
                        'last_auto_sync': now.isoformat(),
                        'next_sync_scheduled': next_sync.isoformat()
                    })\
                    .eq('user_id', user_id)\
                    .execute()

                print(f"      ✅ Sync completed: +{sync_result['documents_added']} added, "
                      f"~{sync_result['documents_updated']} updated, "
                      f"-{sync_result['documents_skipped']} skipped")
                logger.info(f"      ⏰ Next sync: {next_sync.strftime('%Y-%m-%d %H:%M UTC')}")

            except Exception as user_error:
                logger.error(f"      ❌ Error syncing for user {user_token.get('user_id')}: {str(user_error)}")

                # Still update next_sync_scheduled to avoid retry spam
                # but keep a reasonable retry interval
                next_retry = now + timedelta(hours=1)
                try:
                    supabase.table('google_drive_tokens')\
                        .update({'next_sync_scheduled': next_retry.isoformat()})\
                        .eq('user_id', user_token.get('user_id'))\
                        .execute()
                    logger.info(f"      🔄 Scheduled retry in 1 hour: {next_retry.strftime('%Y-%m-%d %H:%M UTC')}")
                except Exception as update_error:
                    logger.error(f"      ⚠️  Could not update retry time: {str(update_error)}")

        logger.info(f"\n{'='*60}")
        logger.info(f"✅ Automatic Sync Job Completed: {datetime.now(timezone.utc).isoformat()}")
        logger.info(f"{'='*60}\n")

    except Exception as e:
        logger.error(f"\n❌ Fatal error in automatic sync job: {str(e)}")
        logger.info(f"{'='*60}\n")


def start_scheduler(check_interval_minutes: int = 5):
    """
    Start the background scheduler for automatic syncs.

    Args:
        check_interval_minutes: How often to check for due syncs (default: 5 minutes)
    """
    global scheduler

    if scheduler is not None and scheduler.running:
        print("⚠️  Scheduler is already running")
        return

    scheduler = BackgroundScheduler(timezone='UTC')

    # Add job to run every N minutes
    # coalesce=True: Combine multiple missed runs into one
    # max_instances=1: Only allow one instance at a time
    # misfire_grace_time=300: Allow job to run up to 5 minutes late before skipping
    scheduler.add_job(
        func=process_automatic_syncs,
        trigger=IntervalTrigger(minutes=check_interval_minutes),
        id='google_drive_auto_sync',
        name='Google Drive Automatic Sync',
        replace_existing=True,
        coalesce=True,
        max_instances=1,
        misfire_grace_time=300
    )

    scheduler.start()

    logger.info(f"\n{'='*60}")
    logger.info(f"🚀 Google Drive Sync Scheduler Started")
    logger.info(f"   ⏱️  Check interval: {check_interval_minutes} minutes")
    logger.info(f"   🕐 Started at: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    logger.info(f"{'='*60}\n")


def stop_scheduler():
    """
    Stop the background scheduler.
    """
    global scheduler

    if scheduler is not None and scheduler.running:
        scheduler.shutdown(wait=True)
        print("\n🛑 Google Drive Sync Scheduler Stopped\n")


def get_scheduler_status() -> dict:
    """
    Get the current status of the scheduler.

    Returns:
        dict: Scheduler status information
    """
    if scheduler is None:
        return {
            'running': False,
            'jobs': []
        }

    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            'id': job.id,
            'name': job.name,
            'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None
        })

    return {
        'running': scheduler.running,
        'jobs': jobs
    }
