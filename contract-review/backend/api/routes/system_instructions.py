"""
System instructions management routes
Handles per-user AI customization
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import asyncio

from auth import get_current_user, require_admin
from database import get_supabase
from system_instructions_loader import get_system_instructions_for_user
from validation import validate_uuid
from logger_config import get_logger
from cache import get_cached_system_instructions, cache_system_instructions, invalidate_user_cache
from errors import handle_exception

logger = get_logger(__name__)
router = APIRouter(prefix="/api/system-instructions", tags=["system-instructions"])
supabase = get_supabase()


class SystemInstructionsRequest(BaseModel):
    instructions: str


@router.get("/{user_id}")
async def get_system_instructions(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get system instructions for a user"""
    try:
        validate_uuid(user_id, "user_id")

        # Users can only get their own instructions (unless admin)
        if current_user['role'] != 'admin' and current_user['id'] != user_id:
            raise HTTPException(status_code=403, detail="Not authorized")

        # Check cache first
        cached_instructions = get_cached_system_instructions(user_id)
        if cached_instructions is not None:
            logger.info(f"📋 Cache hit for system instructions: {user_id}")
            return {
                'success': True,
                'instructions': cached_instructions,
                'user_id': user_id,
                'cached': True
            }

        logger.info(f"📋 Loading system instructions for user: {user_id}")

        # Fetch complete user data including name, client info
        try:
            user_result = await asyncio.to_thread(
                lambda: supabase.table('users')
                    .select('id, email, name, role, client_id, clients(name, assistant_name)')
                    .eq('id', user_id)
                    .single()
                    .execute()
            )
        except Exception as db_error:
            logger.error(f"❌ Database query failed: {str(db_error)}")
            raise HTTPException(status_code=500, detail=f"Database error: {str(db_error)}")

        if not user_result.data:
            logger.warning(f"⚠️  User not found: {user_id}")
            raise HTTPException(status_code=404, detail="User not found")

        user_data = user_result.data
        logger.debug(f"   User data fetched: {user_data.get('email')}")

        # Safely extract client info (handle None/null cases)
        clients_data = user_data.get('clients') if user_data.get('clients') is not None else {}

        # Prepare user data with client info
        enriched_user_data = {
            'id': user_data['id'],
            'email': user_data['email'],
            'name': user_data.get('name', 'User'),
            'role': user_data['role'],
            'client_id': user_data.get('client_id'),
            'client_name': clients_data.get('name') if isinstance(clients_data, dict) else None,
            'assistant_name': clients_data.get('assistant_name') if isinstance(clients_data, dict) else None,
        }

        logger.debug(f"   Loading instructions with data: name={enriched_user_data.get('name')}, client={enriched_user_data.get('client_name')}")

        try:
            instructions = get_system_instructions_for_user(
                user_id=user_id,
                user_data=enriched_user_data
            )
        except Exception as loader_error:
            logger.error(f"❌ Instructions loader failed: {str(loader_error)}")
            raise HTTPException(status_code=500, detail=f"Failed to load instructions: {str(loader_error)}")

        logger.info(f"✅ System instructions loaded successfully for user: {user_id}")

        # Cache the instructions for future requests (1 hour TTL)
        cache_system_instructions(user_id, instructions)

        return {
            'success': True,
            'instructions': instructions,
            'user_id': user_id,
            'cached': False
        }
    except HTTPException:
        raise
    except Exception as e:
        handle_exception(e, "load system instructions", logger)


@router.post("/{user_id}")
async def update_system_instructions(
    user_id: str,
    request: SystemInstructionsRequest,
    current_user: dict = Depends(require_admin)
):
    """Update system instructions for a user (admin only)"""
    try:
        validate_uuid(user_id, "user_id")
        
        # Update in database
        result = await asyncio.to_thread(
            lambda: supabase.table('users')\
                .update({'system_instructions': request.instructions})\
                .eq('id', user_id)\
                .execute()
        )
        
        if not result.data:
            raise HTTPException(status_code=404, detail="User not found")

        # Invalidate cache so next request gets fresh instructions
        invalidate_user_cache(user_id)

        logger.info(f"✅ System instructions updated for user: {user_id}")
        
        return {
            'success': True,
            'message': 'System instructions updated',
            'user_id': user_id
        }
    except HTTPException:
        raise
    except Exception as e:
        handle_exception(e, "update system instructions", logger)


# ============================================================================
# Contract Type System Instructions
# ============================================================================

VALID_CONTRACT_TYPES = ['vendor', 'customer', 'employment', 'dpa', 'general', 'other']


@router.get("/contract-types/{contract_type}")
async def get_contract_type_instructions(
    contract_type: str,
    current_user: dict = Depends(require_admin)
):
    """Get system instructions for a specific contract type (admin only)"""
    try:
        # Validate contract type
        if contract_type not in VALID_CONTRACT_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid contract type. Must be one of: {', '.join(VALID_CONTRACT_TYPES)}"
            )

        logger.info(f"📋 Loading system instructions for contract type: {contract_type}")

        # Try to fetch from database
        result = await asyncio.to_thread(
            lambda: supabase.table('contract_type_instructions')
                .select('instructions')
                .eq('contract_type', contract_type)
                .single()
                .execute()
        )

        if result.data and result.data.get('instructions'):
            instructions = result.data['instructions']
            logger.info(f"✅ Loaded custom instructions for contract type: {contract_type}")
        else:
            # Load default instructions from XML file
            import os
            # Map contract type to actual XML filename
            contract_type_upper = contract_type.upper()
            default_file = f"system_instructions/{contract_type_upper}_CONTRACT_SYSTEM_INSTRUCTIONS.xml"

            if os.path.exists(default_file):
                with open(default_file, 'r') as f:
                    instructions = f.read()
                logger.info(f"📄 Loaded default XML instructions for contract type: {contract_type} from {default_file}")
            else:
                # Return generic fallback
                instructions = f"""You are analyzing {contract_type} contracts. Provide thorough analysis focusing on:

1. Key terms and conditions
2. Risk assessment and red flags
3. Compliance requirements
4. Negotiation points
5. Recommendations

Provide analysis in structured JSON format with risk_score, key_terms, red_flags, and recommendations."""
                logger.info(f"⚠️  Using fallback instructions for contract type: {contract_type}")

        return {
            'success': True,
            'instructions': instructions,
            'contract_type': contract_type
        }

    except HTTPException:
        raise
    except Exception as e:
        handle_exception(e, f"load system instructions for contract type {contract_type}", logger)


@router.post("/contract-types/{contract_type}")
async def update_contract_type_instructions(
    contract_type: str,
    request: SystemInstructionsRequest,
    current_user: dict = Depends(require_admin)
):
    """Update system instructions for a specific contract type (admin only)"""
    try:
        # Validate contract type
        if contract_type not in VALID_CONTRACT_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid contract type. Must be one of: {', '.join(VALID_CONTRACT_TYPES)}"
            )

        logger.info(f"💾 Updating system instructions for contract type: {contract_type}")

        # Upsert to database (insert or update)
        result = await asyncio.to_thread(
            lambda: supabase.table('contract_type_instructions')
                .upsert({
                    'contract_type': contract_type,
                    'instructions': request.instructions,
                    'updated_at': 'now()'
                }, on_conflict='contract_type')
                .execute()
        )

        logger.info(f"✅ System instructions updated for contract type: {contract_type}")

        return {
            'success': True,
            'message': f'System instructions updated for {contract_type} contracts',
            'contract_type': contract_type
        }

    except HTTPException:
        raise
    except Exception as e:
        handle_exception(e, f"update system instructions for contract type {contract_type}", logger)
