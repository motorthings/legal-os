"""
Google Drive integration routes
Handles OAuth, sync, and folder management
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional
import asyncio
import os

from auth import get_current_user
from database import get_supabase
from services.google_drive_sync import (
    sync_folder, sync_files, get_connection_status, disconnect_user, list_folder_files, GoogleDriveSyncError, create_placeholder_documents
)
from services.oauth_crypto import encrypt_token
from validation import validate_uuid
from logger_config import get_logger
from google_auth_oauthlib.flow import Flow

logger = get_logger(__name__)
router = APIRouter(prefix="/api/google-drive", tags=["google-drive"])
supabase = get_supabase()


class SyncRequest(BaseModel):
    folder_id: Optional[str] = None
    file_ids: Optional[list[str]] = None


class SyncSettingsRequest(BaseModel):
    sync_frequency: str  # manual, daily, weekly, monthly
    folder_id: Optional[str] = None


@router.get("/auth")
async def google_drive_auth(
    current_user: dict = Depends(get_current_user)
):
    """Initiate Google Drive OAuth flow"""
    try:
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                    "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [os.getenv("GOOGLE_REDIRECT_URI")]
                }
            },
            scopes=['https://www.googleapis.com/auth/drive.readonly']
        )
        
        flow.redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
        
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        
        # Store state in database (expires in 10 minutes for security)
        from datetime import datetime, timezone, timedelta
        expires_at = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()

        await asyncio.to_thread(
            lambda: supabase.table('oauth_states').insert({
                'state': state,
                'user_id': current_user['id'],
                'provider': 'google_drive',
                'expires_at': expires_at
            }).execute()
        )
        
        return {
            'success': True,
            'authorization_url': authorization_url
        }
        
    except Exception as e:
        logger.error(f"❌ OAuth init error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/callback")
async def google_drive_callback(
    code: str,
    state: str
):
    """Handle Google Drive OAuth callback"""
    try:
        # Verify state
        state_result = await asyncio.to_thread(
            lambda: supabase.table('oauth_states')\
                .select('*')\
                .eq('state', state)\
                .single()\
                .execute()
        )
        
        if not state_result.data:
            raise HTTPException(status_code=400, detail="Invalid state")
            
        user_id = state_result.data['user_id']
        
        # Exchange code for tokens
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                    "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [os.getenv("GOOGLE_REDIRECT_URI")]
                }
            },
            scopes=['https://www.googleapis.com/auth/drive.readonly']
        )
        flow.redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
        flow.fetch_token(code=code)
        
        credentials = flow.credentials
        
        # Encrypt and store tokens
        encrypted_token = encrypt_token(credentials.token)
        encrypted_refresh = encrypt_token(credentials.refresh_token) if credentials.refresh_token else None
        
        await asyncio.to_thread(
            lambda: supabase.table('google_drive_tokens').upsert({
                'user_id': user_id,
                'access_token_encrypted': encrypted_token,
                'refresh_token_encrypted': encrypted_refresh,
                'token_expires_at': credentials.expiry.isoformat() if credentials.expiry else None,
                'scopes': credentials.scopes,
                'is_active': True
            }, on_conflict='user_id').execute()
        )
        
        # Delete used state
        await asyncio.to_thread(
            lambda: supabase.table('oauth_states').delete().eq('state', state).execute()
        )
        
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        return RedirectResponse(url=f"{frontend_url}/documents?google_drive_connected=true")
        
    except Exception as e:
        logger.error(f"❌ OAuth callback error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_google_drive_status(
    current_user: dict = Depends(get_current_user)
):
    """Get Google Drive connection status"""
    try:
        status = get_connection_status(current_user['id'])
        return {'success': True, **status}
    except Exception as e:
        logger.error(f"❌ Status check error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files/{folder_id}")
async def get_folder_files(
    folder_id: str,
    current_user: dict = Depends(get_current_user)
):
    """List files in a Google Drive folder"""
    try:
        files = list_folder_files(current_user['id'], folder_id)
        return {
            'success': True,
            'files': files
        }
    except GoogleDriveSyncError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"❌ List files error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync")
async def sync_google_drive(
    request: SyncRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Trigger manual Google Drive sync"""
    try:
        # Check if syncing specific files or a folder
        if request.file_ids:
            # Create placeholder documents synchronously BEFORE background task
            # This ensures they appear in the UI immediately
            await asyncio.to_thread(
                create_placeholder_documents,
                current_user['id'],
                request.file_ids
            )

            background_tasks.add_task(
                sync_files,
                current_user['id'],
                request.file_ids
            )
            message = f'Sync started for {len(request.file_ids)} file(s) in background'
        else:
            background_tasks.add_task(
                sync_folder,
                current_user['id'],
                request.folder_id
            )
            message = 'Sync started in background'

        return {
            'success': True,
            'message': message
        }
    except GoogleDriveSyncError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Sync error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-document/{document_id}")
async def sync_single_document(
    document_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Sync a specific Google Drive document by its file ID"""
    try:
        # Sync single document in background
        background_tasks.add_task(
            sync_files,
            current_user['id'],
            [document_id]  # sync_files expects a list of file IDs
        )

        return {
            'success': True,
            'message': f'Document {document_id} sync started in background'
        }
    except GoogleDriveSyncError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Document sync error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/disconnect")
async def disconnect_google_drive(
    current_user: dict = Depends(get_current_user)
):
    """Disconnect Google Drive"""
    try:
        disconnect_user(current_user['id'])
        return {
            'success': True,
            'message': 'Google Drive disconnected'
        }
    except Exception as e:
        logger.error(f"❌ Disconnect error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sync-history")
async def get_sync_history(
    current_user: dict = Depends(get_current_user),
    limit: int = 10
):
    """Get recent sync history"""
    try:
        result = await asyncio.to_thread(
            lambda: supabase.table('google_drive_sync_log')\
                .select('*')\
                .eq('user_id', current_user['id'])\
                .order('started_at', desc=True)\
                .limit(limit)\
                .execute()
        )
        
        return {
            'success': True,
            'history': result.data
        }
    except Exception as e:
        logger.error(f"❌ Sync history error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sync-settings")
async def get_sync_settings(
    current_user: dict = Depends(get_current_user)
):
    """Get sync settings"""
    try:
        result = await asyncio.to_thread(
            lambda: supabase.table('google_drive_tokens')\
                .select('sync_frequency, next_sync_scheduled')\
                .eq('user_id', current_user['id'])\
                .single()\
                .execute()
        )

        if not result.data:
            raise HTTPException(status_code=404, detail="Not connected to Google Drive")

        return {
            'success': True,
            **result.data
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Get settings error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/sync-settings")
async def update_sync_settings(
    request: SyncSettingsRequest,
    current_user: dict = Depends(get_current_user)
):
    """Update sync settings"""
    try:
        update_data = {
            'sync_frequency': request.sync_frequency
        }
        if request.folder_id:
            update_data['folder_id'] = request.folder_id
            
        result = await asyncio.to_thread(
            lambda: supabase.table('google_drive_tokens')\
                .update(update_data)\
                .eq('user_id', current_user['id'])\
                .execute()
        )
        
        return {
            'success': True,
            'settings': result.data[0] if result.data else None
        }
    except Exception as e:
        logger.error(f"❌ Update settings error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
