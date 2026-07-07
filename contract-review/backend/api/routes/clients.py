"""
Client management routes
Handles listing and retrieving client information
"""
from fastapi import APIRouter, Depends, HTTPException
import asyncio

from auth import get_current_user, require_admin
from database import get_supabase
from validation import validate_uuid
from logger_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/clients", tags=["clients"])
supabase = get_supabase()


@router.get("")
async def list_clients(current_user: dict = Depends(require_admin)):
    """
    Get all clients

    Requires: admin role

    Returns:
        List of all clients with basic stats
    """
    try:
        logger.info(f"\n🏢 Loading all clients")

        # Fetch clients from database
        clients_result = await asyncio.to_thread(
            lambda: supabase.table('clients')
                .select('*')
                .order('created_at', desc=True)
                .execute()
        )

        clients = clients_result.data

        # Enrich each client with stats
        enriched_clients = []
        for client in clients:
            # Count conversations
            conv_result = await asyncio.to_thread(
                lambda: supabase.table('conversations')
                    .select('id', count='exact')
                    .eq('client_id', client['id'])
                    .execute()
            )

            # Count documents
            docs_result = await asyncio.to_thread(
                lambda: supabase.table('documents')
                    .select('id', count='exact')
                    .eq('client_id', client['id'])
                    .execute()
            )

            # Count users
            users_result = await asyncio.to_thread(
                lambda: supabase.table('users')
                    .select('id', count='exact')
                    .eq('client_id', client['id'])
                    .execute()
            )

            enriched_clients.append({
                **client,
                'conversation_count': conv_result.count or 0,
                'document_count': docs_result.count or 0,
                'user_count': users_result.count or 0
            })

        logger.info(f"   ✅ Loaded {len(enriched_clients)} clients")

        return {
            'success': True,
            'clients': enriched_clients,
            'count': len(enriched_clients)
        }

    except Exception as e:
        logger.error(f"❌ Error loading clients: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{client_id}")
async def get_client(client_id: str, current_user: dict = Depends(get_current_user)):
    """
    Get a single client by ID

    Args:
        client_id: UUID of the client
        current_user: Authenticated user from JWT token

    Returns:
        Client details with stats
    """
    try:
        # Validate UUID
        validate_uuid(client_id, "client_id")

        logger.info(f"\n🏢 Loading client: {client_id}")

        # Verify user has access to this client (unless admin)
        if current_user['role'] != 'admin' and current_user.get('client_id') != client_id:
            raise HTTPException(status_code=403, detail="Not authorized to access this client")

        # Fetch client from database
        client_result = await asyncio.to_thread(
            lambda: supabase.table('clients')
                .select('*')
                .eq('id', client_id)
                .single()
                .execute()
        )

        if not client_result.data:
            raise HTTPException(status_code=404, detail="Client not found")

        client = client_result.data

        # Count conversations
        conv_result = await asyncio.to_thread(
            lambda: supabase.table('conversations')
                .select('id', count='exact')
                .eq('client_id', client_id)
                .execute()
        )

        # Count documents
        docs_result = await asyncio.to_thread(
            lambda: supabase.table('documents')
                .select('id', count='exact')
                .eq('client_id', client_id)
                .execute()
        )

        # Count users
        users_result = await asyncio.to_thread(
            lambda: supabase.table('users')
                .select('id', count='exact')
                .eq('client_id', client_id)
                .execute()
        )

        enriched_client = {
            **client,
            'conversation_count': conv_result.count or 0,
            'document_count': docs_result.count or 0,
            'user_count': users_result.count or 0
        }

        logger.info(f"   ✅ Loaded client: {client.get('name', 'Unknown')}")

        return {
            'success': True,
            'client': enriched_client
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error loading client: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
