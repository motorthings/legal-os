"""
User management routes
Handles user CRUD, prompts, and profile operations
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from typing import Optional, List
from pydantic import BaseModel, EmailStr
import asyncio

from auth import get_current_user, require_admin
from database import get_supabase
from config import get_default_client_id
from validation import validate_uuid, generate_secure_password
from logger_config import get_logger
# from services.quick_prompts_generator import generate_quick_prompts  # Module doesn't exist

logger = get_logger(__name__)
router = APIRouter(prefix="/api/users", tags=["users"])
supabase = get_supabase()


# ============================================================================
# Request/Response Models
# ============================================================================

class UserCreateRequest(BaseModel):
    email: EmailStr
    name: str
    role: str = "user"


class UserUpdateRequest(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None


class PromptCreateRequest(BaseModel):
    title: str
    prompt_text: str
    category: Optional[str] = None


class PromptUpdateRequest(BaseModel):
    title: Optional[str] = None
    prompt_text: Optional[str] = None
    category: Optional[str] = None


# ============================================================================
# User CRUD Operations
# ============================================================================

@router.get("")
async def list_users(
    current_user: dict = Depends(require_admin)
):
    """List all users (admin only)"""
    try:
        result = await asyncio.to_thread(
            lambda: supabase.table('users')\
                .select('id, email, name, role, created_at')\
                .order('created_at', desc=True)\
                .execute()
        )

        return {
            'success': True,
            'users': result.data
        }

    except Exception as e:
        logger.error(f"❌ Error listing users: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
async def create_user(
    request: UserCreateRequest,
    current_user: dict = Depends(require_admin)
):
    """Create a new user (admin only)"""
    try:
        # Generate secure temporary password
        temp_password = generate_secure_password(16)

        # Auto-assign default client
        client_id = get_default_client_id()

        # Create user in Supabase Auth
        auth_result = await asyncio.to_thread(
            lambda: supabase.auth.admin.create_user({
                "email": request.email,
                "password": temp_password,
                "email_confirm": True
            })
        )

        user_id = auth_result.user.id

        # Create user profile in database
        profile_data = {
            'id': user_id,
            'email': request.email,
            'name': request.name,
            'role': request.role,
            'client_id': client_id
        }

        await asyncio.to_thread(
            lambda: supabase.table('users').insert(profile_data).execute()
        )

        logger.info(f"✅ User created: {request.email}")

        return {
            'success': True,
            'user_id': user_id,
            'email': request.email,
            'temporary_password': temp_password,
            'message': 'User created successfully. Send password via secure channel.'
        }

    except Exception as e:
        logger.error(f"❌ Error creating user: {str(e)}")
        raise HTTPException(status_code=500, detail=f"User creation failed: {str(e)}")


@router.put("/{user_id}")
async def update_user(
    user_id: str,
    request: UserUpdateRequest,
    current_user: dict = Depends(require_admin)
):
    """Update user profile (admin only)"""
    try:
        validate_uuid(user_id, "user_id")

        update_data = {}
        if request.name is not None:
            update_data['name'] = request.name
        if request.role is not None:
            update_data['role'] = request.role

        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")

        result = await asyncio.to_thread(
            lambda: supabase.table('users')\
                .update(update_data)\
                .eq('id', user_id)\
                .execute()
        )

        if not result.data:
            raise HTTPException(status_code=404, detail="User not found")

        return {
            'success': True,
            'user': result.data[0]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating user: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{user_id}/resend-invitation")
async def resend_invitation(
    user_id: str,
    current_user: dict = Depends(require_admin)
):
    """Resend password reset email to user"""
    try:
        validate_uuid(user_id, "user_id")

        # Get user email
        user_result = await asyncio.to_thread(
            lambda: supabase.table('users')\
                .select('email')\
                .eq('id', user_id)\
                .single()\
                .execute()
        )

        if not user_result.data:
            raise HTTPException(status_code=404, detail="User not found")

        email = user_result.data['email']

        # Send password reset email via Supabase
        await asyncio.to_thread(
            lambda: supabase.auth.reset_password_for_email(email)
        )

        logger.info(f"✅ Password reset email sent to: {email}")

        return {
            'success': True,
            'message': f'Password reset email sent to {email}'
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error resending invitation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# User Prompts (Quick Templates)
# ============================================================================

@router.get("/{user_id}/prompts")
async def get_user_prompts(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get all quick prompts for a user"""
    try:
        validate_uuid(user_id, "user_id")

        # Users can only access their own prompts (unless admin)
        if current_user['role'] != 'admin' and current_user['id'] != user_id:
            raise HTTPException(status_code=403, detail="Not authorized")

        result = await asyncio.to_thread(
            lambda: supabase.table('user_prompts')\
                .select('*')\
                .eq('user_id', user_id)\
                .order('created_at', desc=True)\
                .execute()
        )

        return {
            'success': True,
            'prompts': result.data
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching prompts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{user_id}/prompts")
async def create_prompt(
    user_id: str,
    request: PromptCreateRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create a new quick prompt"""
    try:
        validate_uuid(user_id, "user_id")

        # Users can only create their own prompts
        if current_user['id'] != user_id:
            raise HTTPException(status_code=403, detail="Not authorized")

        prompt_data = {
            'user_id': user_id,
            'title': request.title,
            'prompt_text': request.prompt_text,
            'category': request.category
        }

        result = await asyncio.to_thread(
            lambda: supabase.table('user_prompts').insert(prompt_data).execute()
        )

        return {
            'success': True,
            'prompt': result.data[0]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error creating prompt: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/prompts/{prompt_id}")
async def update_prompt(
    prompt_id: str,
    request: PromptUpdateRequest,
    current_user: dict = Depends(get_current_user)
):
    """Update a quick prompt"""
    try:
        validate_uuid(prompt_id, "prompt_id")

        # Get prompt to check ownership
        prompt_result = await asyncio.to_thread(
            lambda: supabase.table('user_prompts')\
                .select('*')\
                .eq('id', prompt_id)\
                .single()\
                .execute()
        )

        if not prompt_result.data:
            raise HTTPException(status_code=404, detail="Prompt not found")

        # Users can only update their own prompts
        if prompt_result.data['user_id'] != current_user['id']:
            raise HTTPException(status_code=403, detail="Not authorized")

        update_data = {}
        if request.title is not None:
            update_data['title'] = request.title
        if request.prompt_text is not None:
            update_data['prompt_text'] = request.prompt_text
        if request.category is not None:
            update_data['category'] = request.category

        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")

        result = await asyncio.to_thread(
            lambda: supabase.table('user_prompts')\
                .update(update_data)\
                .eq('id', prompt_id)\
                .execute()
        )

        return {
            'success': True,
            'prompt': result.data[0]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating prompt: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/prompts/{prompt_id}")
async def delete_prompt(
    prompt_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a quick prompt"""
    try:
        validate_uuid(prompt_id, "prompt_id")

        # Get prompt to check ownership
        prompt_result = await asyncio.to_thread(
            lambda: supabase.table('user_prompts')\
                .select('*')\
                .eq('id', prompt_id)\
                .single()\
                .execute()
        )

        if not prompt_result.data:
            raise HTTPException(status_code=404, detail="Prompt not found")

        # Users can only delete their own prompts
        if prompt_result.data['user_id'] != current_user['id']:
            raise HTTPException(status_code=403, detail="Not authorized")

        await asyncio.to_thread(
            lambda: supabase.table('user_prompts')\
                .delete()\
                .eq('id', prompt_id)\
                .execute()
        )

        return {
            'success': True,
            'message': 'Prompt deleted successfully'
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting prompt: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Auto-Generated Quick Prompts
# ============================================================================

@router.post("/{user_id}/generate-prompts")
async def generate_user_prompts(
    user_id: str,
    current_user: dict = Depends(require_admin)
):
    """
    Auto-generate quick prompts based on user's selected functions.
    Called after system instructions are deployed.
    Admin only - this is part of the deployment flow.
    """
    try:
        validate_uuid(user_id, "user_id")

        # Get user's extraction data to determine selected functions
        extraction_result = await asyncio.to_thread(
            lambda: supabase.table('extractions')\
                .select('extraction_json, client_id')\
                .eq('client_id', user_id)\
                .eq('deployment_status', 'deployed')\
                .order('created_at', desc=True)\
                .limit(1)\
                .execute()
        )

        if not extraction_result.data:
            raise HTTPException(
                status_code=404,
                detail="No deployed extraction found for this user"
            )

        extraction_data = extraction_result.data[0]['extraction_json']

        # Extract selected functions from extraction data
        # The extraction JSON contains the 10-function selection
        selected_functions = extraction_data.get('selected_functions', [])

        if not selected_functions:
            # Fallback: try to infer from pain points or other data
            # For now, use all 10 functions if not explicitly specified
            selected_functions = [
                "priority_sorting_context_switching",
                "decision_support_tradeoff_analysis",
                "strategic_thinking_future_planning",
                "meeting_prep_followup",
                "communication_drafting",
                "problem_breakdown_root_cause",
                "goal_setting_tracking",
                "learning_skill_development",
                "workflow_optimization",
                "ideation_brainstorming"
            ]

        # Get user context for personalization
        user_result = await asyncio.to_thread(
            lambda: supabase.table('users')\
                .select('name, email')\
                .eq('id', user_id)\
                .single()\
                .execute()
        )

        user_context = {
            'name': user_result.data.get('name'),
            'email': user_result.data.get('email')
        }

        # Generate prompts
        prompts = generate_quick_prompts(
            selected_functions=selected_functions,
            max_prompts=7,
            user_context=user_context
        )

        # Delete existing auto-generated prompts for this user
        await asyncio.to_thread(
            lambda: supabase.table('user_prompts')\
                .delete()\
                .eq('user_id', user_id)\
                .eq('is_auto_generated', True)\
                .execute()
        )

        # Insert new prompts
        prompt_records = [
            {
                'user_id': user_id,
                'title': prompt['text'],
                'prompt_text': prompt['text'],
                'category': prompt['category'],
                'is_auto_generated': True,
                'metadata': {
                    'function': prompt['function'],
                    'generated_at': 'deployment'
                }
            }
            for prompt in prompts
        ]

        result = await asyncio.to_thread(
            lambda: supabase.table('user_prompts')\
                .insert(prompt_records)\
                .execute()
        )

        logger.info(f"✅ Generated {len(prompts)} quick prompts for user {user_id}")

        return {
            'success': True,
            'prompts_generated': len(prompts),
            'prompts': result.data
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error generating prompts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}/quick-prompts-preview")
async def preview_quick_prompts(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Preview auto-generated prompts without saving them.
    Useful for the alignment review page.
    """
    try:
        validate_uuid(user_id, "user_id")

        # Users can only preview their own prompts
        if current_user['role'] != 'admin' and current_user['id'] != user_id:
            raise HTTPException(status_code=403, detail="Not authorized")

        # Get user's latest extraction
        extraction_result = await asyncio.to_thread(
            lambda: supabase.table('extractions')\
                .select('extraction_json')\
                .eq('client_id', user_id)\
                .order('created_at', desc=True)\
                .limit(1)\
                .execute()
        )

        if not extraction_result.data:
            return {
                'success': True,
                'prompts': [],
                'message': 'No extraction data found'
            }

        extraction_data = extraction_result.data[0]['extraction_json']
        selected_functions = extraction_data.get('selected_functions', [])

        if not selected_functions:
            # Use all functions as fallback
            selected_functions = [
                "priority_sorting_context_switching",
                "decision_support_tradeoff_analysis",
                "strategic_thinking_future_planning",
                "meeting_prep_followup",
                "communication_drafting"
            ]

        prompts = generate_quick_prompts(
            selected_functions=selected_functions,
            max_prompts=7
        )

        return {
            'success': True,
            'prompts': prompts
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error previewing prompts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
