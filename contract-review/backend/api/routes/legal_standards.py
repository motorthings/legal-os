"""
Legal Standards management routes
Handles CRUD operations for configurable legal standards
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
import asyncio
import json

from auth import get_current_user, require_admin
from database import get_supabase
from validation import validate_uuid
from logger_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/legal-standards", tags=["legal-standards"])
supabase = get_supabase()


@router.get("")
async def list_legal_standards(
    contract_type: Optional[str] = Query(None, description="Filter by contract type"),
    category: Optional[str] = Query(None, description="Filter by category"),
    is_active: Optional[bool] = Query(True, description="Filter by active status"),
    client_id: Optional[str] = Query(None, description="Filter by client (admin only)"),
    current_user: dict = Depends(get_current_user)
):
    """
    List all legal standards with optional filters

    Query params:
        contract_type: Filter by contract type (vendor, customer, employment, dpa, general, all)
        category: Filter by category (payment_terms, liability, etc.)
        is_active: Show only active standards (default: true)
        client_id: Filter by client (admin only, defaults to current user's client)

    Returns:
        List of legal standards matching filters
    """
    try:
        logger.info(f"\n📋 Loading legal standards")

        # Build query
        query = supabase.table('legal_standards').select('*')

        # Apply filters
        if is_active is not None:
            query = query.eq('is_active', is_active)

        if contract_type:
            query = query.eq('contract_type', contract_type)

        if category:
            query = query.eq('category', category)

        # Handle client filtering
        if current_user['role'] == 'admin':
            # Admins can filter by specific client or see all
            if client_id:
                validate_uuid(client_id, "client_id")
                query = query.eq('client_id', client_id)
        else:
            # Non-admin users see standards for their client + defaults
            user_client_id = current_user.get('client_id')
            if user_client_id:
                # Standards where client_id is NULL (defaults) OR matches user's client
                query = query.or_(f'client_id.is.null,client_id.eq.{user_client_id}')
            else:
                # No client_id - only show defaults
                query = query.is_('client_id', 'null')

        # Execute query
        result = await asyncio.to_thread(
            lambda: query.order('category', desc=False)
                         .order('term_name', desc=False)
                         .execute()
        )

        standards = result.data or []

        logger.info(f"   ✅ Loaded {len(standards)} legal standards")

        return {
            'success': True,
            'standards': standards,
            'count': len(standards)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error loading legal standards: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{standard_id}")
async def get_legal_standard(
    standard_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get a single legal standard by ID

    Args:
        standard_id: UUID of the legal standard

    Returns:
        Legal standard details
    """
    try:
        validate_uuid(standard_id, "standard_id")

        logger.info(f"\n📋 Loading legal standard: {standard_id}")

        # Fetch standard
        result = await asyncio.to_thread(
            lambda: supabase.table('legal_standards')
                .select('*')
                .eq('id', standard_id)
                .single()
                .execute()
        )

        if not result.data:
            raise HTTPException(status_code=404, detail="Legal standard not found")

        standard = result.data

        # Verify user has access (non-admins can only access their client's standards + defaults)
        if current_user['role'] != 'admin':
            standard_client_id = standard.get('client_id')
            user_client_id = current_user.get('client_id')

            # Allow if standard is default (NULL) or matches user's client
            if standard_client_id is not None and standard_client_id != user_client_id:
                raise HTTPException(
                    status_code=403,
                    detail="Not authorized to access this legal standard"
                )

        logger.info(f"   ✅ Loaded legal standard")

        return {
            'success': True,
            'standard': standard
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error loading legal standard: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
async def create_legal_standard(
    standard: dict,
    current_user: dict = Depends(require_admin)
):
    """
    Create a new legal standard (admin only)

    Request body:
        {
            "client_id": "uuid or null for default",
            "contract_type": "vendor|customer|employment|dpa|general|all",
            "category": "payment_terms|liability|termination|etc",
            "term_name": "net_days|liability_cap|notice_period|etc",
            "acceptable_values": {JSON validation rules},
            "violation_severity": "red_flag|yellow_flag|info",
            "description": "Short description",
            "rationale": "Why this standard exists (optional)",
            "recommendation": "What to do if violated (optional)"
        }

    Returns:
        Created legal standard
    """
    try:
        logger.info(f"\n✨ Creating legal standard")

        # Validate required fields
        required_fields = ['contract_type', 'category', 'term_name', 'acceptable_values',
                          'violation_severity', 'description']
        for field in required_fields:
            if field not in standard or not standard[field]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing required field: {field}"
                )

        # Validate contract_type
        valid_contract_types = ['vendor', 'customer', 'employment', 'dpa', 'general', 'all']
        if standard['contract_type'] not in valid_contract_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid contract_type. Must be one of: {', '.join(valid_contract_types)}"
            )

        # Validate violation_severity
        valid_severities = ['red_flag', 'yellow_flag', 'info']
        if standard['violation_severity'] not in valid_severities:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid violation_severity. Must be one of: {', '.join(valid_severities)}"
            )

        # Validate client_id if provided
        if 'client_id' in standard and standard['client_id']:
            validate_uuid(standard['client_id'], "client_id")

        # Set created_by to current user
        standard['created_by'] = current_user['id']

        # Ensure acceptable_values is JSON
        if isinstance(standard.get('acceptable_values'), dict):
            standard['acceptable_values'] = json.dumps(standard['acceptable_values'])

        # Create standard
        result = await asyncio.to_thread(
            lambda: supabase.table('legal_standards')
                .insert(standard)
                .execute()
        )

        created_standard = result.data[0] if result.data else None

        if not created_standard:
            raise HTTPException(status_code=500, detail="Failed to create legal standard")

        logger.info(f"   ✅ Created legal standard: {created_standard.get('term_name')}")

        return {
            'success': True,
            'standard': created_standard
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error creating legal standard: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{standard_id}")
async def update_legal_standard(
    standard_id: str,
    updates: dict,
    current_user: dict = Depends(require_admin)
):
    """
    Update an existing legal standard (admin only)

    Args:
        standard_id: UUID of the legal standard to update
        updates: Fields to update (partial update supported)

    Returns:
        Updated legal standard
    """
    try:
        validate_uuid(standard_id, "standard_id")

        logger.info(f"\n📝 Updating legal standard: {standard_id}")

        # Verify standard exists
        existing_result = await asyncio.to_thread(
            lambda: supabase.table('legal_standards')
                .select('*')
                .eq('id', standard_id)
                .single()
                .execute()
        )

        if not existing_result.data:
            raise HTTPException(status_code=404, detail="Legal standard not found")

        # Validate contract_type if being updated
        if 'contract_type' in updates:
            valid_contract_types = ['vendor', 'customer', 'employment', 'dpa', 'general', 'all']
            if updates['contract_type'] not in valid_contract_types:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid contract_type. Must be one of: {', '.join(valid_contract_types)}"
                )

        # Validate violation_severity if being updated
        if 'violation_severity' in updates:
            valid_severities = ['red_flag', 'yellow_flag', 'info']
            if updates['violation_severity'] not in valid_severities:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid violation_severity. Must be one of: {', '.join(valid_severities)}"
                )

        # Validate client_id if being updated
        if 'client_id' in updates and updates['client_id']:
            validate_uuid(updates['client_id'], "client_id")

        # Ensure acceptable_values is JSON if being updated
        if 'acceptable_values' in updates and isinstance(updates.get('acceptable_values'), dict):
            updates['acceptable_values'] = json.dumps(updates['acceptable_values'])

        # Remove fields that shouldn't be updated directly
        updates.pop('id', None)
        updates.pop('created_at', None)
        updates.pop('created_by', None)

        # Update standard
        result = await asyncio.to_thread(
            lambda: supabase.table('legal_standards')
                .update(updates)
                .eq('id', standard_id)
                .execute()
        )

        updated_standard = result.data[0] if result.data else None

        if not updated_standard:
            raise HTTPException(status_code=500, detail="Failed to update legal standard")

        logger.info(f"   ✅ Updated legal standard")

        return {
            'success': True,
            'standard': updated_standard
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating legal standard: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{standard_id}")
async def delete_legal_standard(
    standard_id: str,
    hard_delete: bool = Query(False, description="Permanently delete instead of deactivating"),
    current_user: dict = Depends(require_admin)
):
    """
    Delete or deactivate a legal standard (admin only)

    Args:
        standard_id: UUID of the legal standard to delete
        hard_delete: If true, permanently delete. If false (default), just set is_active=false

    Returns:
        Success confirmation
    """
    try:
        validate_uuid(standard_id, "standard_id")

        logger.info(f"\n🗑️  {'Deleting' if hard_delete else 'Deactivating'} legal standard: {standard_id}")

        # Verify standard exists
        existing_result = await asyncio.to_thread(
            lambda: supabase.table('legal_standards')
                .select('*')
                .eq('id', standard_id)
                .single()
                .execute()
        )

        if not existing_result.data:
            raise HTTPException(status_code=404, detail="Legal standard not found")

        if hard_delete:
            # Permanently delete
            await asyncio.to_thread(
                lambda: supabase.table('legal_standards')
                    .delete()
                    .eq('id', standard_id)
                    .execute()
            )
            logger.info(f"   ✅ Permanently deleted legal standard")
        else:
            # Soft delete (deactivate)
            await asyncio.to_thread(
                lambda: supabase.table('legal_standards')
                    .update({'is_active': False})
                    .eq('id', standard_id)
                    .execute()
            )
            logger.info(f"   ✅ Deactivated legal standard")

        return {
            'success': True,
            'message': 'Legal standard deleted' if hard_delete else 'Legal standard deactivated'
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting legal standard: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/categories/list")
async def list_categories(
    contract_type: Optional[str] = Query(None, description="Filter by contract type"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get list of unique categories used in legal standards

    Useful for populating category dropdowns in UI

    Query params:
        contract_type: Filter categories by contract type (optional)

    Returns:
        List of unique category names
    """
    try:
        logger.info(f"\n📋 Loading legal standard categories")

        # Build query
        query = supabase.table('legal_standards').select('category').eq('is_active', True)

        if contract_type:
            query = query.eq('contract_type', contract_type)

        # Handle client filtering
        if current_user['role'] != 'admin':
            user_client_id = current_user.get('client_id')
            if user_client_id:
                query = query.or_(f'client_id.is.null,client_id.eq.{user_client_id}')
            else:
                query = query.is_('client_id', 'null')

        # Execute query
        result = await asyncio.to_thread(lambda: query.execute())

        # Extract unique categories
        categories = list(set(item['category'] for item in result.data if item.get('category')))
        categories.sort()

        logger.info(f"   ✅ Found {len(categories)} unique categories")

        return {
            'success': True,
            'categories': categories,
            'count': len(categories)
        }

    except Exception as e:
        logger.error(f"❌ Error loading categories: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
