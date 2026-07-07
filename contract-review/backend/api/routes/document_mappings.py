"""
Document Mapping Routes
Manages the relationship between documents and system instruction template slots
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import asyncio

from auth import require_admin
from database import get_supabase
from validation import validate_uuid
from logger_config import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["document_mappings"])
supabase = get_supabase()


class DocumentMapping(BaseModel):
    template_slot: str
    document_ids: List[str]  # Can map multiple docs to one slot


class UpdateMappingsRequest(BaseModel):
    mappings: List[DocumentMapping]


class Document(BaseModel):
    id: str
    filename: str
    uploaded_at: str
    file_size: Optional[int] = None
    is_core_document: bool = False


@router.get("/api/clients/{client_id}/document-mappings")
async def get_document_mappings(
    client_id: str,
    current_user: dict = Depends(require_admin)
):
    """Get current document mappings for a client"""
    try:
        validate_uuid(client_id, "client_id")

        # Get all mappings for this client
        result = await asyncio.to_thread(
            lambda: supabase.table('system_instruction_document_mappings')\
                .select('*, documents(id, filename, uploaded_at, file_size, is_core_document)')\
                .eq('client_id', client_id)\
                .order('template_slot')\
                .order('display_order')\
                .execute()
        )

        # Group by template_slot
        mappings_by_slot: Dict[str, List[dict]] = {}
        for mapping in result.data or []:
            slot = mapping['template_slot']
            if slot not in mappings_by_slot:
                mappings_by_slot[slot] = []

            doc = mapping.get('documents')
            if doc:
                mappings_by_slot[slot].append({
                    'mapping_id': mapping['id'],
                    'document_id': doc['id'],
                    'filename': doc['filename'],
                    'uploaded_at': doc['uploaded_at'],
                    'file_size': doc.get('file_size'),
                    'display_order': mapping['display_order']
                })

        return {
            'success': True,
            'mappings': mappings_by_slot
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Get document mappings error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/clients/{client_id}/documents")
async def get_client_documents(
    client_id: str,
    current_user: dict = Depends(require_admin)
):
    """Get all documents available for mapping for a client"""
    try:
        validate_uuid(client_id, "client_id")

        result = await asyncio.to_thread(
            lambda: supabase.table('documents')\
                .select('id, filename, uploaded_at, file_size, is_core_document, processed')\
                .eq('client_id', client_id)\
                .eq('processed', True)\
                .order('filename')\
                .execute()
        )

        return {
            'success': True,
            'documents': result.data or []
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Get client documents error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/clients/{client_id}/document-mappings")
async def update_document_mappings(
    client_id: str,
    request: UpdateMappingsRequest,
    current_user: dict = Depends(require_admin)
):
    """Update document mappings for a client"""
    try:
        validate_uuid(client_id, "client_id")

        # Validate all document IDs
        all_doc_ids = []
        for mapping in request.mappings:
            for doc_id in mapping.document_ids:
                validate_uuid(doc_id, "document_id")
                all_doc_ids.append(doc_id)

        # Delete all existing mappings for this client
        await asyncio.to_thread(
            lambda: supabase.table('system_instruction_document_mappings')\
                .delete()\
                .eq('client_id', client_id)\
                .execute()
        )

        # Insert new mappings
        new_mappings = []
        for mapping in request.mappings:
            for idx, doc_id in enumerate(mapping.document_ids):
                new_mappings.append({
                    'client_id': client_id,
                    'document_id': doc_id,
                    'template_slot': mapping.template_slot,
                    'display_order': idx
                })

        if new_mappings:
            await asyncio.to_thread(
                lambda: supabase.table('system_instruction_document_mappings')\
                    .insert(new_mappings)\
                    .execute()
            )

        logger.info(f"✅ Updated document mappings for client {client_id}: {len(new_mappings)} mappings")

        return {
            'success': True,
            'message': f'Updated {len(new_mappings)} document mappings'
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Update document mappings error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/clients/{client_id}/regenerate-instructions")
async def regenerate_instructions(
    client_id: str,
    current_user: dict = Depends(require_admin)
):
    """Regenerate system instructions with updated document mappings"""
    try:
        validate_uuid(client_id, "client_id")

        # Import here to avoid circular dependency
        from services.solomon_stage2 import regenerate_instructions as regen

        # Get the most recent extraction for this client
        # Include all statuses where instructions can be regenerated
        extraction_result = await asyncio.to_thread(
            lambda: supabase.table('interview_extractions')\
                .select('id')\
                .eq('client_id', client_id)\
                .in_('status', [
                    'extraction_complete',
                    'instructions_generated',
                    'approved',
                    'deployed'
                ])\
                .order('created_at', desc=True)\
                .limit(1)\
                .execute()
        )

        if not extraction_result.data:
            raise HTTPException(
                status_code=404,
                detail="No completed extraction found for this client. "
                       "Complete an interview and extraction first."
            )

        extraction_id = extraction_result.data[0]['id']

        # Regenerate instructions
        result = await regen(client_id=client_id, extraction_id=extraction_id)

        if result['status'] == 'failed':
            raise HTTPException(status_code=500, detail=result['error'])

        return {
            'success': True,
            'message': 'System instructions regenerated successfully',
            'instructions_length': result['generation_metadata']['instructions_length']
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Regenerate instructions error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
