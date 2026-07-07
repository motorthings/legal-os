"""
Theme Settings API Routes

Endpoints for managing application theme/styling settings.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from typing import Optional
import asyncio
import uuid
import os

from auth import get_current_user
from database import get_supabase
from logger_config import get_logger

router = APIRouter(tags=["Theme"])
logger = get_logger(__name__)
supabase = get_supabase()


class ThemeSettings(BaseModel):
    """Theme settings model"""
    # Brand colors
    color_primary: Optional[str] = Field(None, pattern=r'^#[0-9a-fA-F]{6}$')
    color_primary_hover: Optional[str] = Field(None, pattern=r'^#[0-9a-fA-F]{6}$')
    color_secondary: Optional[str] = Field(None, pattern=r'^#[0-9a-fA-F]{6}$')
    color_text_on_primary: Optional[str] = Field(None, pattern=r'^#[0-9a-fA-F]{6}$')
    color_text_on_secondary: Optional[str] = Field(None, pattern=r'^#[0-9a-fA-F]{6}$')

    # Background colors
    color_bg_page: Optional[str] = Field(None, pattern=r'^#[0-9a-fA-F]{6}$')
    color_bg_card: Optional[str] = Field(None, pattern=r'^#[0-9a-fA-F]{6}$')
    color_bg_hover: Optional[str] = Field(None, pattern=r'^#[0-9a-fA-F]{6}$')

    # Text colors
    color_text_primary: Optional[str] = Field(None, pattern=r'^#[0-9a-fA-F]{6}$')
    color_text_secondary: Optional[str] = Field(None, pattern=r'^#[0-9a-fA-F]{6}$')
    color_text_muted: Optional[str] = Field(None, pattern=r'^#[0-9a-fA-F]{6}$')

    # Border colors
    color_border: Optional[str] = Field(None, pattern=r'^#[0-9a-fA-F]{6}$')
    color_border_focus: Optional[str] = Field(None, pattern=r'^#[0-9a-fA-F]{6}$')

    # Status colors
    color_success: Optional[str] = Field(None, pattern=r'^#[0-9a-fA-F]{6}$')
    color_warning: Optional[str] = Field(None, pattern=r'^#[0-9a-fA-F]{6}$')
    color_error: Optional[str] = Field(None, pattern=r'^#[0-9a-fA-F]{6}$')

    # Typography
    font_family_heading: Optional[str] = None
    font_weight_heading: Optional[str] = None
    font_family_body: Optional[str] = None
    font_weight_body: Optional[str] = None
    font_size_base: Optional[str] = None

    # Border radius
    border_radius_sm: Optional[str] = None
    border_radius_md: Optional[str] = None
    border_radius_lg: Optional[str] = None

    # Panel/Card edge styling
    panel_border_width: Optional[str] = None
    panel_border_color: Optional[str] = Field(None, pattern=r'^#[0-9a-fA-F]{6}$')
    panel_shadow_size: Optional[str] = None
    panel_shadow_color: Optional[str] = Field(None, pattern=r'^#[0-9a-fA-F]{6}$')

    # Header styling
    header_logo_url: Optional[str] = None
    header_bg_color: Optional[str] = Field(None, pattern=r'^#[0-9a-fA-F]{6}$')
    header_title_color: Optional[str] = Field(None, pattern=r'^#[0-9a-fA-F]{6}$')
    header_nav_color: Optional[str] = Field(None, pattern=r'^#[0-9a-fA-F]{6}$')
    header_nav_active_color: Optional[str] = Field(None, pattern=r'^#[0-9a-fA-F]{6}$')
    header_font_size: Optional[str] = None
    header_height: Optional[str] = None
    page_title_font_size: Optional[str] = None


@router.get("/api/theme")
async def get_theme_settings(current_user: dict = Depends(get_current_user)):
    """Get theme settings for the current user's client"""
    try:
        client_id = current_user.get('client_id')

        result = await asyncio.to_thread(
            lambda: supabase.table('theme_settings')
            .select('*')
            .eq('client_id', client_id)
            .single()
            .execute()
        )

        if not result.data:
            # Return default theme if none exists
            return {
                "success": True,
                "theme": get_default_theme()
            }

        return {
            "success": True,
            "theme": result.data
        }

    except Exception as e:
        logger.error(f"Error fetching theme settings: {e}")
        # Return default theme on error
        return {
            "success": True,
            "theme": get_default_theme()
        }


@router.put("/api/theme")
async def update_theme_settings(
    settings: ThemeSettings,
    current_user: dict = Depends(get_current_user)
):
    """Update theme settings (admin only)"""
    try:
        # Check admin role
        if current_user.get('role') != 'admin':
            raise HTTPException(status_code=403, detail="Admin access required")

        client_id = current_user.get('client_id')

        # Build update data, excluding None values
        update_data = {k: v for k, v in settings.dict().items() if v is not None}

        if not update_data:
            raise HTTPException(status_code=400, detail="No settings provided")

        # Check if theme settings exist
        existing = await asyncio.to_thread(
            lambda: supabase.table('theme_settings')
            .select('id')
            .eq('client_id', client_id)
            .single()
            .execute()
        )

        if existing.data:
            # Update existing
            result = await asyncio.to_thread(
                lambda: supabase.table('theme_settings')
                .update(update_data)
                .eq('client_id', client_id)
                .execute()
            )
        else:
            # Insert new
            update_data['client_id'] = client_id
            result = await asyncio.to_thread(
                lambda: supabase.table('theme_settings')
                .insert(update_data)
                .execute()
            )

        logger.info(f"Theme settings updated for client {client_id}")

        return {
            "success": True,
            "message": "Theme settings updated",
            "theme": result.data[0] if result.data else update_data
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating theme settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/theme/reset")
async def reset_theme_settings(current_user: dict = Depends(get_current_user)):
    """Reset theme settings to defaults (admin only)"""
    try:
        if current_user.get('role') != 'admin':
            raise HTTPException(status_code=403, detail="Admin access required")

        client_id = current_user.get('client_id')
        default_theme = get_default_theme()

        # Remove non-column fields
        default_theme.pop('id', None)
        default_theme.pop('created_at', None)
        default_theme.pop('updated_at', None)
        default_theme['client_id'] = client_id

        result = await asyncio.to_thread(
            lambda: supabase.table('theme_settings')
            .upsert(default_theme, on_conflict='client_id')
            .execute()
        )

        logger.info(f"Theme settings reset for client {client_id}")

        return {
            "success": True,
            "message": "Theme settings reset to defaults",
            "theme": result.data[0] if result.data else default_theme
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting theme settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


SUPABASE_URL = os.environ.get("SUPABASE_URL")
ALLOWED_LOGO_TYPES = ["image/png", "image/jpeg", "image/gif", "image/svg+xml", "image/webp"]
MAX_LOGO_SIZE = 2 * 1024 * 1024  # 2MB


@router.post("/api/theme/logo")
async def upload_logo(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload a logo image (admin only)"""
    try:
        if current_user.get('role') != 'admin':
            raise HTTPException(status_code=403, detail="Admin access required")

        # Validate file type
        if file.content_type not in ALLOWED_LOGO_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed: PNG, JPEG, GIF, SVG, WebP"
            )

        # Read and validate file size
        file_content = await file.read()
        if len(file_content) > MAX_LOGO_SIZE:
            raise HTTPException(status_code=400, detail="Logo file too large. Maximum size is 2MB")

        client_id = current_user.get('client_id')

        # Generate unique filename
        file_ext = file.filename.split('.')[-1] if '.' in file.filename else 'png'
        unique_filename = f"logo_{client_id}_{uuid.uuid4()}.{file_ext}"
        storage_path = f"logos/{unique_filename}"

        # Upload to Supabase Storage (using documents bucket or create a separate one)
        logger.info(f"Uploading logo to storage: {storage_path}")

        upload_result = await asyncio.to_thread(
            lambda: supabase.storage.from_('documents').upload(
                storage_path,
                file_content,
                file_options={"content-type": file.content_type}
            )
        )

        # Get public URL
        logo_url = f"{SUPABASE_URL}/storage/v1/object/public/documents/{storage_path}"

        # Update theme settings with new logo URL
        existing = await asyncio.to_thread(
            lambda: supabase.table('theme_settings')
            .select('id')
            .eq('client_id', client_id)
            .single()
            .execute()
        )

        if existing.data:
            await asyncio.to_thread(
                lambda: supabase.table('theme_settings')
                .update({'header_logo_url': logo_url})
                .eq('client_id', client_id)
                .execute()
            )
        else:
            await asyncio.to_thread(
                lambda: supabase.table('theme_settings')
                .insert({'client_id': client_id, 'header_logo_url': logo_url})
                .execute()
            )

        logger.info(f"Logo uploaded successfully for client {client_id}")

        return {
            "success": True,
            "message": "Logo uploaded successfully",
            "logo_url": logo_url
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading logo: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/theme/logo")
async def delete_logo(current_user: dict = Depends(get_current_user)):
    """Remove the logo (admin only)"""
    try:
        if current_user.get('role') != 'admin':
            raise HTTPException(status_code=403, detail="Admin access required")

        client_id = current_user.get('client_id')

        # Set logo URL to null
        await asyncio.to_thread(
            lambda: supabase.table('theme_settings')
            .update({'header_logo_url': None})
            .eq('client_id', client_id)
            .execute()
        )

        logger.info(f"Logo removed for client {client_id}")

        return {
            "success": True,
            "message": "Logo removed successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing logo: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def get_default_theme() -> dict:
    """Return default theme settings"""
    return {
        "color_primary": "#6366f1",
        "color_primary_hover": "#4f46e5",
        "color_secondary": "#8b5cf6",
        "color_text_on_primary": "#ffffff",
        "color_text_on_secondary": "#ffffff",
        "color_bg_page": "#0a0a0a",
        "color_bg_card": "#111111",
        "color_bg_hover": "#1a1a1a",
        "color_text_primary": "#ffffff",
        "color_text_secondary": "#a1a1aa",
        "color_text_muted": "#71717a",
        "color_border": "#27272a",
        "color_border_focus": "#6366f1",
        "color_success": "#22c55e",
        "color_warning": "#f59e0b",
        "color_error": "#ef4444",
        "font_family_heading": "Inter",
        "font_weight_heading": "600",
        "font_family_body": "Inter",
        "font_weight_body": "400",
        "font_size_base": "16px",
        "border_radius_sm": "0.25rem",
        "border_radius_md": "0.5rem",
        "border_radius_lg": "0.75rem",
        "panel_border_width": "1px",
        "panel_border_color": "#27272a",
        "panel_shadow_size": "1px",
        "panel_shadow_color": "#000000",
        "header_logo_url": None,
        "header_bg_color": "#111111",
        "header_title_color": "#14b8a6",
        "header_nav_color": "#a1a1aa",
        "header_nav_active_color": "#14b8a6",
        "header_font_size": "20px",
        "header_height": "64px",
        "page_title_font_size": "32px"
    }
