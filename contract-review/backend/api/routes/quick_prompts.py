"""
Quick Prompts API Routes
Handles CRUD operations for user quick prompts (activation shortcuts for AI assistant functions)

Created: November 21, 2025
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from auth import get_current_user, require_admin
from database import get_supabase
from services.quick_prompt_generator import (
    generate_quick_prompts,
    save_quick_prompts,
    get_user_quick_prompts,
    update_quick_prompt,
    delete_quick_prompt,
    increment_usage_count
)
from validation import validate_uuid
from logger_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/quick-prompts", tags=["quick_prompts"])
supabase = get_supabase()


# ============================================================================
# Request/Response Models
# ============================================================================

class GeneratePromptsRequest(BaseModel):
    """Request body for generating quick prompts"""
    selected_functions: List[str] = Field(..., min_items=5, max_items=5, description="5 function names from Solomon Stage 2")
    extraction_json: Optional[dict] = Field(None, description="Optional extraction data for context-aware prompts")


class CreatePromptRequest(BaseModel):
    """Request body for creating a custom prompt"""
    prompt_text: str = Field(..., min_length=1, max_length=500, description="Text of the quick prompt")
    function_name: Optional[str] = Field(None, description="Function this prompt activates (optional)")


class UpdatePromptRequest(BaseModel):
    """Request body for updating a prompt"""
    prompt_text: Optional[str] = Field(None, min_length=1, max_length=500, description="Updated prompt text")
    active: Optional[bool] = Field(None, description="Whether prompt is active")
    display_order: Optional[int] = Field(None, description="Display order")


class QuickPromptResponse(BaseModel):
    """Response model for a quick prompt"""
    id: str
    user_id: str
    client_id: Optional[str]
    prompt_text: str
    function_name: Optional[str]
    system_generated: bool
    editable: bool
    active: bool
    display_order: Optional[int]
    usage_count: int
    created_at: str
    updated_at: str


# ============================================================================
# Quick Prompt Routes
# ============================================================================

@router.post("/generate")
async def generate_prompts_for_user(
    request: GeneratePromptsRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Auto-generate quick prompts based on selected functions from Solomon Stage 2

    This endpoint is typically called automatically after system instructions are deployed.
    Generates 10 quick prompts (2 per function) for the 5 selected functions.
    """
    try:
        user_id = current_user['id']
        client_id = current_user.get('client_id')

        logger.info(f"[Quick Prompts API] Generating prompts for user {user_id}")

        # Validate function names
        if len(request.selected_functions) != 5:
            raise HTTPException(
                status_code=400,
                detail=f"Expected 5 functions, got {len(request.selected_functions)}"
            )

        # Generate prompts
        prompts = generate_quick_prompts(
            user_id=user_id,
            client_id=client_id,
            selected_functions=request.selected_functions,
            extraction_json=request.extraction_json
        )

        # Save to database
        result = save_quick_prompts(prompts)

        if not result['success']:
            raise HTTPException(status_code=500, detail=result.get('error', 'Failed to save prompts'))

        logger.info(f"[Quick Prompts API] Successfully generated {result['count']} prompts")

        return {
            "success": True,
            "count": result['count'],
            "prompts": result['prompts']
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Quick Prompts API] Error generating prompts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def get_quick_prompts(
    active_only: bool = True,
    current_user: dict = Depends(get_current_user)
):
    """
    Get all quick prompts for the current user

    Query Parameters:
    - active_only: If true, only return active prompts (default: true)
    """
    try:
        user_id = current_user['id']

        logger.info(f"[Quick Prompts API] Fetching prompts for user {user_id} (active_only={active_only})")

        prompts = get_user_quick_prompts(user_id, active_only=active_only)

        return {
            "success": True,
            "count": len(prompts),
            "prompts": prompts
        }

    except Exception as e:
        logger.error(f"[Quick Prompts API] Error fetching prompts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/")
async def create_custom_prompt(
    request: CreatePromptRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new custom quick prompt

    Users can add their own prompts beyond the auto-generated ones.
    """
    try:
        user_id = current_user['id']
        client_id = current_user.get('client_id')

        logger.info(f"[Quick Prompts API] Creating custom prompt for user {user_id}")

        # Get current max display_order
        existing_prompts = get_user_quick_prompts(user_id, active_only=False)
        max_order = max([p.get('display_order', 0) for p in existing_prompts], default=0)

        # Create prompt object
        prompt_data = {
            "user_id": user_id,
            "client_id": client_id,
            "prompt_text": request.prompt_text,
            "function_name": request.function_name,
            "system_generated": False,  # User-created
            "editable": True,
            "active": True,
            "display_order": max_order + 1,
            "usage_count": 0
        }

        # Insert into database
        result = supabase.table('user_quick_prompts').insert(prompt_data).execute()

        if len(result.data) == 0:
            raise HTTPException(status_code=500, detail="Failed to create prompt")

        logger.info(f"[Quick Prompts API] Successfully created custom prompt")

        return {
            "success": True,
            "prompt": result.data[0]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Quick Prompts API] Error creating prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{prompt_id}")
async def update_prompt(
    prompt_id: str,
    request: UpdatePromptRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Update a quick prompt (edit text, toggle active, change order)

    Users can edit any prompt marked as editable=true.
    """
    try:
        validate_uuid(prompt_id)
        user_id = current_user['id']

        logger.info(f"[Quick Prompts API] Updating prompt {prompt_id} for user {user_id}")

        # Build updates dict (only include fields that were provided)
        updates = {}
        if request.prompt_text is not None:
            updates['prompt_text'] = request.prompt_text
        if request.active is not None:
            updates['active'] = request.active
        if request.display_order is not None:
            updates['display_order'] = request.display_order

        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")

        # Update prompt
        result = update_quick_prompt(prompt_id, user_id, updates)

        if not result['success']:
            raise HTTPException(status_code=404, detail=result.get('error', 'Prompt not found'))

        logger.info(f"[Quick Prompts API] Successfully updated prompt {prompt_id}")

        return {
            "success": True,
            "prompt": result['prompt']
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Quick Prompts API] Error updating prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{prompt_id}")
async def delete_prompt(
    prompt_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a quick prompt

    Users can delete any prompt they own.
    """
    try:
        validate_uuid(prompt_id)
        user_id = current_user['id']

        logger.info(f"[Quick Prompts API] Deleting prompt {prompt_id} for user {user_id}")

        # Delete prompt
        result = delete_quick_prompt(prompt_id, user_id)

        if not result['success']:
            raise HTTPException(status_code=404, detail=result.get('error', 'Prompt not found'))

        logger.info(f"[Quick Prompts API] Successfully deleted prompt {prompt_id}")

        return {
            "success": True,
            "message": "Prompt deleted successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Quick Prompts API] Error deleting prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{prompt_id}/use")
async def track_prompt_usage(
    prompt_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Track usage of a quick prompt (increment usage_count)

    Call this endpoint when a user clicks/uses a quick prompt.
    Used for analytics to understand which prompts are most valuable.
    """
    try:
        validate_uuid(prompt_id)

        logger.info(f"[Quick Prompts API] Tracking usage for prompt {prompt_id}")

        # Increment usage count
        result = increment_usage_count(prompt_id)

        if not result['success']:
            # Don't fail the request if usage tracking fails
            logger.warning(f"[Quick Prompts API] Failed to track usage: {result.get('error')}")

        return {
            "success": True,
            "usage_count": result.get('usage_count', 0)
        }

    except Exception as e:
        # Log error but don't fail the request
        logger.error(f"[Quick Prompts API] Error tracking usage: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# ============================================================================
# Admin Routes
# ============================================================================

@router.get("/admin/users/{user_id}")
async def admin_get_user_prompts(
    user_id: str,
    active_only: bool = False,
    current_user: dict = Depends(require_admin)
):
    """
    Admin endpoint to view quick prompts for any user

    Requires admin authentication.
    """
    try:
        validate_uuid(user_id)

        logger.info(f"[Quick Prompts API] Admin fetching prompts for user {user_id}")

        prompts = get_user_quick_prompts(user_id, active_only=active_only)

        return {
            "success": True,
            "user_id": user_id,
            "count": len(prompts),
            "prompts": prompts
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Quick Prompts API] Admin error fetching prompts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/admin/stats")
async def admin_get_prompt_stats(
    current_user: dict = Depends(require_admin)
):
    """
    Admin endpoint to get quick prompt usage statistics

    Returns analytics on prompt usage across all users.
    """
    try:
        logger.info(f"[Quick Prompts API] Admin fetching prompt stats")

        # Get total prompts count
        total_result = supabase.table('user_quick_prompts').select('id', count='exact').execute()
        total_prompts = total_result.count

        # Get active prompts count
        active_result = supabase.table('user_quick_prompts').select('id', count='exact').eq('active', True).execute()
        active_prompts = active_result.count

        # Get system-generated vs user-created
        system_result = supabase.table('user_quick_prompts').select('id', count='exact').eq('system_generated', True).execute()
        system_generated = system_result.count

        # Get most used prompts
        popular_result = (
            supabase.table('user_quick_prompts')
            .select('prompt_text, function_name, usage_count')
            .order('usage_count', desc=True)
            .limit(10)
            .execute()
        )

        return {
            "success": True,
            "stats": {
                "total_prompts": total_prompts,
                "active_prompts": active_prompts,
                "inactive_prompts": total_prompts - active_prompts,
                "system_generated": system_generated,
                "user_created": total_prompts - system_generated
            },
            "most_used_prompts": popular_result.data
        }

    except Exception as e:
        logger.error(f"[Quick Prompts API] Error fetching stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
