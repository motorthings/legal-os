"""
Notion integration routes
Handles OAuth, page sync, and workspace management
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional, List
import asyncio
import os

from auth import get_current_user
from database import get_supabase
from services.notion_sync import (
    sync_pages, get_connection_status as get_notion_status,
    disconnect_user as disconnect_notion, NotionSyncError,
    get_accessible_pages
)
from services.oauth_crypto import encrypt_token
from logger_config import get_logger
import httpx

logger = get_logger(__name__)
router = APIRouter(prefix="/api/notion", tags=["notion"])
supabase = get_supabase()


class SyncRequest(BaseModel):
    page_ids: List[str]


class SyncSettingsRequest(BaseModel):
    sync_frequency: str
    default_page_ids: Optional[List[str]] = None


@router.get("/auth")
async def notion_auth(
    current_user: dict = Depends(get_current_user)
):
    """Initiate Notion OAuth flow"""
    try:
        client_id = os.getenv("NOTION_CLIENT_ID")
        redirect_uri = os.getenv("NOTION_REDIRECT_URI")
        
        import secrets
        state = secrets.token_urlsafe(32)
        
        # Store state
        await asyncio.to_thread(
            lambda: supabase.table('oauth_states').insert({
                'state': state,
                'user_id': current_user['id'],
                'provider': 'notion'
            }).execute()
        )
        
        auth_url = f"https://api.notion.com/v1/oauth/authorize?client_id={client_id}&response_type=code&owner=user&redirect_uri={redirect_uri}&state={state}"
        
        return {
            'success': True,
            'authorization_url': auth_url
        }
    except Exception as e:
        logger.error(f"❌ Notion OAuth init error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/callback")
async def notion_callback(
    code: str,
    state: str
):
    """Handle Notion OAuth callback"""
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
        
        # Exchange code for token
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.notion.com/v1/oauth/token",
                auth=(os.getenv("NOTION_CLIENT_ID"), os.getenv("NOTION_CLIENT_SECRET")),
                json={"grant_type": "authorization_code", "code": code, "redirect_uri": os.getenv("NOTION_REDIRECT_URI")}
            )
            
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="Token exchange failed")
            
        token_data = response.json()
        
        # Encrypt and store token
        encrypted_token = encrypt_token(token_data['access_token'])
        
        await asyncio.to_thread(
            lambda: supabase.table('notion_tokens').upsert({
                'user_id': user_id,
                'access_token': encrypted_token,
                'workspace_id': token_data.get('workspace_id'),
                'workspace_name': token_data.get('workspace_name'),
                'is_active': True
            }).execute()
        )
        
        # Delete used state
        await asyncio.to_thread(
            lambda: supabase.table('oauth_states').delete().eq('state', state).execute()
        )
        
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        return RedirectResponse(url=f"{frontend_url}/documents?notion_connected=true")
        
    except Exception as e:
        logger.error(f"❌ Notion callback error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_notion_status_endpoint(
    current_user: dict = Depends(get_current_user)
):
    """Get Notion connection status"""
    try:
        status = get_notion_status(current_user['id'])
        return {'success': True, **status}
    except Exception as e:
        logger.error(f"❌ Status check error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pages")
async def list_notion_pages(
    current_user: dict = Depends(get_current_user)
):
    """List accessible Notion pages"""
    try:
        pages = get_accessible_pages(current_user['id'])
        return {
            'success': True,
            'pages': pages
        }
    except NotionSyncError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"❌ List pages error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync")
async def sync_notion_pages(
    request: SyncRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Trigger manual Notion page sync"""
    try:
        background_tasks.add_task(
            sync_pages,
            current_user['id'],
            request.page_ids
        )
        
        return {
            'success': True,
            'message': f'Syncing {len(request.page_ids)} page(s) in background'
        }
    except NotionSyncError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"❌ Sync error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/disconnect")
async def disconnect_notion_endpoint(
    current_user: dict = Depends(get_current_user)
):
    """Disconnect Notion"""
    try:
        disconnect_notion(current_user['id'])
        return {
            'success': True,
            'message': 'Notion disconnected'
        }
    except Exception as e:
        logger.error(f"❌ Disconnect error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sync-history")
async def get_notion_sync_history(
    current_user: dict = Depends(get_current_user),
    limit: int = 10
):
    """Get recent sync history"""
    try:
        result = await asyncio.to_thread(
            lambda: supabase.table('notion_sync_log')\
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
async def get_notion_sync_settings(
    current_user: dict = Depends(get_current_user)
):
    """Get sync settings"""
    try:
        result = await asyncio.to_thread(
            lambda: supabase.table('notion_tokens')\
                .select('sync_frequency, default_page_ids, next_sync_scheduled')\
                .eq('user_id', current_user['id'])\
                .single()\
                .execute()
        )
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Not connected to Notion")
            
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
async def update_notion_sync_settings(
    request: SyncSettingsRequest,
    current_user: dict = Depends(get_current_user)
):
    """Update sync settings"""
    try:
        update_data = {
            'sync_frequency': request.sync_frequency
        }
        if request.default_page_ids is not None:
            update_data['default_page_ids'] = request.default_page_ids
            
        result = await asyncio.to_thread(
            lambda: supabase.table('notion_tokens')\
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
