"""
Conversation management routes
Handles creation, retrieval, updating, and deletion of conversations
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import Optional, List
from datetime import datetime
import asyncio

from auth import get_current_user
from database import get_supabase
from config import get_default_client_id
from document_processor import process_conversation_to_kb, remove_conversation_from_kb
from validation import validate_uuid
from logger_config import get_logger
from pydantic import BaseModel

logger = get_logger(__name__)
router = APIRouter(prefix="/api/conversations", tags=["conversations"])
supabase = get_supabase()


# ============================================================================
# Request/Response Models
# ============================================================================

class ConversationCreateRequest(BaseModel):
    user_id: str
    title: str = "New Conversation"
    client_id: Optional[str] = None


class ConversationUpdateRequest(BaseModel):
    title: str


class ConversationSearchRequest(BaseModel):
    query: str
    limit: int = 10


# ============================================================================
# Conversation CRUD Operations
# ============================================================================

@router.post("/create")
async def create_conversation(
    request: ConversationCreateRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create a new conversation"""
    try:
        # Auto-assign default client if not provided (single-tenant mode)
        client_id = request.client_id or get_default_client_id()
        logger.info(f"💬 Creating conversation for client: {client_id}")

        # Create conversation in database
        result = await asyncio.to_thread(
            lambda: supabase.table('conversations').insert({
                'client_id': client_id,
                'user_id': request.user_id,
                'title': request.title
            }).execute()
        )

        conversation = result.data[0]
        logger.info(f"✅ Conversation created: {conversation['id']}")

        return {
            'success': True,
            'conversation_id': conversation['id'],
            'client_id': conversation['client_id'],
            'user_id': conversation['user_id'],
            'title': conversation['title'],
            'created_at': conversation['created_at']
        }

    except Exception as e:
        logger.error(f"❌ Error creating conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
    limit: int = 100,
    offset: int = 0
):
    """Get messages in a conversation with pagination"""
    try:
        validate_uuid(conversation_id, "conversation_id")

        # Enforce reasonable limits
        limit = min(limit, 200)

        # Fetch messages ordered by timestamp with pagination
        result = await asyncio.to_thread(
            lambda: supabase.table('messages')
                .select('id, role, content, timestamp', count='exact')
                .eq('conversation_id', conversation_id)
                .order('timestamp', desc=False)
                .limit(limit)
                .offset(offset)
                .execute()
        )

        messages = result.data

        return {
            'success': True,
            'conversation_id': conversation_id,
            'messages': messages,
            'total': result.count,
            'limit': limit,
            'offset': offset
        }

    except Exception as e:
        logger.error(f"❌ Error fetching messages: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{conversation_id}")
async def update_conversation(
    conversation_id: str,
    request: ConversationUpdateRequest,
    current_user: dict = Depends(get_current_user)
):
    """Update conversation (rename)"""
    try:
        validate_uuid(conversation_id, "conversation_id")

        # Update conversation title
        result = await asyncio.to_thread(
            lambda: supabase.table('conversations')\
                .update({'title': request.title})\
                .eq('id', conversation_id)\
                .execute()
        )

        if not result.data:
            raise HTTPException(status_code=404, detail="Conversation not found")

        return {
            'success': True,
            'conversation': result.data[0]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a conversation and all its messages"""
    try:
        validate_uuid(conversation_id, "conversation_id")

        # Delete messages first (foreign key constraint)
        await asyncio.to_thread(
            lambda: supabase.table('messages')\
                .delete()\
                .eq('conversation_id', conversation_id)\
                .execute()
        )

        # Delete conversation
        result = await asyncio.to_thread(
            lambda: supabase.table('conversations')\
                .delete()\
                .eq('id', conversation_id)\
                .execute()
        )

        return {
            'success': True,
            'message': 'Conversation deleted successfully'
        }

    except Exception as e:
        logger.error(f"❌ Error deleting conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Conversation Listing
# ============================================================================

@router.get("")
async def list_conversations(
    user_id: Optional[str] = None,
    client_id: Optional[str] = None,
    limit: int = 100,
    current_user: dict = Depends(get_current_user)
):
    """List conversations - all for admins, user-specific for regular users"""
    try:
        # Admins can see all conversations, regular users only see their own
        is_admin = current_user.get('role') == 'admin'

        # Build query
        query = supabase.table('conversations')\
            .select('*, clients(name), users(name, email)', count='exact')

        # Apply filters
        if not is_admin:
            # Regular users can only see their own conversations
            query = query.eq('user_id', current_user['id'])
        elif user_id:
            # Admin filtering by specific user
            query = query.eq('user_id', user_id)

        if client_id:
            query = query.eq('client_id', client_id)

        # Apply ordering and limit
        query = query.order('updated_at', desc=True).limit(limit)

        result = await asyncio.to_thread(lambda: query.execute())

        conversations = result.data

        # Get message counts for all conversations in a single query (fixes N+1)
        if conversations:
            conversation_ids = [conv['id'] for conv in conversations]

            # Batch fetch message counts using a single query with grouping
            # We use RPC or raw query for efficiency - fall back to in-memory counting
            msg_counts_result = await asyncio.to_thread(
                lambda: supabase.table('messages')
                    .select('conversation_id')
                    .in_('conversation_id', conversation_ids)
                    .execute()
            )

            # Count messages per conversation in memory (single DB query)
            msg_counts = {}
            for msg in (msg_counts_result.data or []):
                conv_id = msg['conversation_id']
                msg_counts[conv_id] = msg_counts.get(conv_id, 0) + 1

            # Attach counts to conversations
            for conv in conversations:
                conv['message_count'] = msg_counts.get(conv['id'], 0)

        return {
            'success': True,
            'conversations': conversations,
            'total': result.count
        }

    except Exception as e:
        logger.error(f"❌ Error listing conversations: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))




# ============================================================================
# Knowledge Base Integration
# ============================================================================

@router.post("/{conversation_id}/add-to-kb")
async def add_conversation_to_knowledge_base(
    conversation_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Add conversation to knowledge base for RAG search"""
    try:
        validate_uuid(conversation_id, "conversation_id")

        # Process conversation in background
        background_tasks.add_task(
            process_conversation_to_kb,
            conversation_id
        )

        return {
            'success': True,
            'message': 'Conversation is being added to knowledge base',
            'conversation_id': conversation_id
        }

    except Exception as e:
        logger.error(f"❌ Error adding conversation to KB: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{conversation_id}/remove-from-kb")
async def remove_conversation_from_knowledge_base(
    conversation_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Remove conversation from knowledge base"""
    try:
        validate_uuid(conversation_id, "conversation_id")

        # Remove conversation chunks
        remove_conversation_from_kb(conversation_id)

        return {
            'success': True,
            'message': 'Conversation removed from knowledge base',
            'conversation_id': conversation_id
        }

    except Exception as e:
        logger.error(f"❌ Error removing conversation from KB: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Archive/Restore
# ============================================================================

@router.post("/{conversation_id}/archive")
async def archive_conversation(
    conversation_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Archive a conversation"""
    try:
        validate_uuid(conversation_id, "conversation_id")

        result = await asyncio.to_thread(
            lambda: supabase.table('conversations')\
                .update({'archived': True})\
                .eq('id', conversation_id)\
                .execute()
        )

        if not result.data:
            raise HTTPException(status_code=404, detail="Conversation not found")

        return {
            'success': True,
            'message': 'Conversation archived',
            'conversation': result.data[0]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error archiving conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{conversation_id}/restore")
async def restore_conversation(
    conversation_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Restore an archived conversation"""
    try:
        validate_uuid(conversation_id, "conversation_id")

        result = await asyncio.to_thread(
            lambda: supabase.table('conversations')\
                .update({'archived': False})\
                .eq('id', conversation_id)\
                .execute()
        )

        if not result.data:
            raise HTTPException(status_code=404, detail="Conversation not found")

        return {
            'success': True,
            'message': 'Conversation restored',
            'conversation': result.data[0]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error restoring conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
