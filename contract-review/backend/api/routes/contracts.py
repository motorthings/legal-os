"""
Contract management routes
Handles contract upload, analysis, retrieval, triage, and review decisions
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, Query
from typing import Optional, List
import asyncio
import uuid
import os

from auth import get_current_user, require_admin
from database import get_supabase
from config import get_default_client_id
from contract_processor import process_contract
from validation import validate_uuid, validate_file_upload, validate_file_size
from logger_config import get_logger

# Celery task imports
try:
    from tasks.contract_tasks import process_contract_task, process_urgent_contract_task
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    logger.warning("Celery not available, falling back to BackgroundTasks")

logger = get_logger(__name__)
router = APIRouter(prefix="/api/contracts", tags=["contracts"])
supabase = get_supabase()
SUPABASE_URL = os.environ.get("SUPABASE_URL")


# ============================================================================
# Contract Upload & Processing
# ============================================================================

@router.post("/upload")
async def upload_contract(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    contract_type: Optional[str] = None,
    counterparty_name: Optional[str] = None,
    redact: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Upload a contract for analysis"""
    try:
        # Validate file
        validate_file_upload(file)

        # Read file content
        file_content = await file.read()
        validate_file_size(file_content)

        # Auto-assign default client
        client_id = current_user.get('client_id') or get_default_client_id()
        user_id = current_user['id']

        # Generate unique filename
        file_ext = file.filename.split('.')[-1] if '.' in file.filename else 'pdf'
        unique_filename = f"{uuid.uuid4()}.{file_ext}"
        storage_path = f"{client_id}/contracts/{unique_filename}"

        # Upload to Supabase Storage
        logger.info(f"Uploading contract {file.filename} to storage: {storage_path}")

        upload_result = await asyncio.to_thread(
            lambda: supabase.storage.from_('documents').upload(
                storage_path,
                file_content,
                file_options={"content-type": file.content_type or "application/pdf"}
            )
        )

        # Get storage URL
        storage_url = f"{SUPABASE_URL}/storage/v1/object/public/documents/{storage_path}"

        # Determine MIME type
        mime_type_map = {
            'pdf': 'application/pdf',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'doc': 'application/msword',
            'txt': 'text/plain'
        }
        mime_type = mime_type_map.get(file_ext.lower(), file.content_type or 'application/octet-stream')

        # Parse redact parameter (comes as string from FormData)
        redact_requested = redact and redact.lower() == 'true'

        # Create database record with contract metadata
        doc_record = {
            'client_id': client_id,
            'uploaded_by': user_id,
            'filename': file.filename,
            'storage_path': storage_path,
            'storage_url': storage_url,
            'file_size': len(file_content),
            'mime_type': mime_type,
            'processed': False,
            'contract_type': contract_type,
            'counterparty_name': counterparty_name,
            'contract_value': None,  # Will be extracted by analysis
            'redact_requested': redact_requested
        }

        result = await asyncio.to_thread(
            lambda: supabase.table('documents').insert(doc_record).execute()
        )

        document = result.data[0]

        logger.info(f"✅ Contract uploaded: {document['id']}")

        # Automatically trigger contract analysis
        # Use Celery if available, otherwise fall back to BackgroundTasks
        use_celery = os.environ.get('USE_CELERY', 'true').lower() == 'true' and CELERY_AVAILABLE

        if use_celery:
            # Queue via Celery for robust async processing
            task = process_contract_task.delay(document['id'])
            logger.info(f"📋 Celery task queued: {document['id']} [Task ID: {task.id}]")

            # Store task ID for status tracking
            await asyncio.to_thread(
                lambda: supabase.table('documents').update({
                    'celery_task_id': task.id
                }).eq('id', document['id']).execute()
            )
        else:
            # Fallback to BackgroundTasks
            background_tasks.add_task(process_contract, document['id'])
            logger.info(f"📋 Background task queued: {document['id']}")

        return {
            'success': True,
            'document_id': document['id'],
            'filename': file.filename,
            'contract_type': contract_type,
            'counterparty_name': counterparty_name,
            'message': 'Contract uploaded successfully. Analysis started in background.'
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.post("/{contract_id}/analyze")
async def analyze_contract_endpoint(
    contract_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Manually trigger contract analysis (or re-analysis)"""
    try:
        validate_uuid(contract_id, "contract_id")

        # Verify document exists
        doc_result = await asyncio.to_thread(
            lambda: supabase.table('documents')
                .select('id')
                .eq('id', contract_id)
                .single()
                .execute()
        )

        if not doc_result.data:
            raise HTTPException(status_code=404, detail="Contract not found")

        # Start analysis (urgent priority for manual re-analysis)
        use_celery = os.environ.get('USE_CELERY', 'true').lower() == 'true' and CELERY_AVAILABLE

        if use_celery:
            # Use urgent queue for manual re-analysis
            task = process_urgent_contract_task.delay(contract_id)
            logger.info(f"🚨 URGENT re-analysis queued: {contract_id} [Task ID: {task.id}]")

            # Store task ID
            await asyncio.to_thread(
                lambda: supabase.table('documents').update({
                    'celery_task_id': task.id
                }).eq('id', contract_id).execute()
            )

            return {
                'success': True,
                'message': 'Contract analysis started (urgent priority)',
                'contract_id': contract_id,
                'task_id': task.id
            }
        else:
            # Fallback to BackgroundTasks
            background_tasks.add_task(process_contract, contract_id)

            return {
                'success': True,
                'message': 'Contract analysis started',
                'contract_id': contract_id
            }

    except Exception as e:
        logger.error(f"❌ Analysis trigger error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{contract_id}/task-status")
async def get_task_status(
    contract_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get Celery task status for a contract

    Useful for real-time progress tracking
    """
    try:
        validate_uuid(contract_id, "contract_id")

        # Get document with task ID
        doc_result = await asyncio.to_thread(
            lambda: supabase.table('documents')
                .select('celery_task_id, processing_status')
                .eq('id', contract_id)
                .single()
                .execute()
        )

        if not doc_result.data:
            raise HTTPException(status_code=404, detail="Contract not found")

        task_id = doc_result.data.get('celery_task_id')
        processing_status = doc_result.data.get('processing_status')

        if not task_id or not CELERY_AVAILABLE:
            return {
                'status': 'no_task',
                'processing_status': processing_status,
                'message': 'No Celery task found (may be using BackgroundTasks)'
            }

        # Query Celery for task status
        from celery.result import AsyncResult
        from celery_app import celery_app as celery_instance

        task = AsyncResult(task_id, app=celery_instance)

        return {
            'task_id': task_id,
            'status': task.state,  # PENDING, STARTED, SUCCESS, FAILURE, RETRY
            'info': task.info if task.state != 'PENDING' else None,
            'result': task.result if task.successful() else None,
            'traceback': str(task.traceback) if task.failed() else None,
            'processing_status': processing_status
        }

    except Exception as e:
        logger.error(f"Error fetching task status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Contract Retrieval & Dashboard
# ============================================================================

@router.get("/dashboard/stats")
async def get_dashboard_stats(
    current_user: dict = Depends(get_current_user)
):
    """Get contract portfolio statistics for dashboard"""
    try:
        # Get stats using database function
        stats_result = await asyncio.to_thread(
            lambda: supabase.rpc('get_contract_stats', {'user_uuid': current_user['id']}).execute()
        )

        if not stats_result.data or len(stats_result.data) == 0:
            # Return zeros if no contracts yet
            return {
                'success': True,
                'stats': {
                    'total_contracts': 0,
                    'high_risk_count': 0,
                    'medium_risk_count': 0,
                    'low_risk_count': 0,
                    'pending_review_count': 0,
                    'human_review_required_count': 0,
                    'avg_risk_score': 0,
                    'avg_confidence_score': 0
                }
            }

        stats = stats_result.data[0]

        return {
            'success': True,
            'stats': {
                'total_contracts': stats['total_contracts'],
                'high_risk_count': stats['high_risk_count'],
                'high_risk_percent': round((stats['high_risk_count'] / stats['total_contracts'] * 100), 1) if stats['total_contracts'] > 0 else 0,
                'medium_risk_count': stats['medium_risk_count'],
                'medium_risk_percent': round((stats['medium_risk_count'] / stats['total_contracts'] * 100), 1) if stats['total_contracts'] > 0 else 0,
                'low_risk_count': stats['low_risk_count'],
                'low_risk_percent': round((stats['low_risk_count'] / stats['total_contracts'] * 100), 1) if stats['total_contracts'] > 0 else 0,
                'pending_review_count': stats['pending_review_count'],
                'human_review_required_count': stats['human_review_required_count'],
                'avg_risk_score': float(stats['avg_risk_score']) if stats['avg_risk_score'] else 0,
                'avg_confidence_score': float(stats['avg_confidence_score']) if stats['avg_confidence_score'] else 0
            }
        }

    except Exception as e:
        logger.error(f"❌ Error fetching dashboard stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def list_contracts(
    current_user: dict = Depends(get_current_user),
    risk_level: Optional[str] = Query(None, regex="^(high|medium|low)$"),
    review_status: Optional[str] = Query(None, regex="^(pending|approved|approved_with_conditions|negotiation_required|rejected)$"),
    human_review_required: Optional[bool] = None,
    processing_status: Optional[str] = Query(None, regex="^(processing|completed|failed)$"),
    limit: int = 50,
    offset: int = 0
):
    """
    List contracts with optional filtering

    Shows contracts immediately after upload with LEFT JOIN to analysis data
    Contracts without analysis yet will show as 'processing' status
    """
    try:
        # Enforce reasonable limits
        limit = min(limit, 100)

        # Build query - start from documents table to show all uploads
        query = supabase.table('documents')\
            .select('''
                id,
                filename,
                counterparty_name,
                contract_type,
                uploaded_at,
                uploaded_by,
                processed,
                processing_status,
                contract_analysis(
                    id,
                    contract_type,
                    parties,
                    effective_date,
                    total_value,
                    overall_risk_level,
                    risk_score,
                    human_review_required,
                    review_status,
                    executive_summary,
                    created_at
                )
            ''', count='exact')

        # Filter by user's documents
        if current_user['role'] != 'admin':
            query = query.eq('uploaded_by', current_user['id'])

        # Apply filters (only for contracts with analysis)
        # Note: Filtering by analysis fields will exclude processing contracts
        if risk_level:
            query = query.eq('contract_analysis.overall_risk_level', risk_level)
        if review_status:
            query = query.eq('contract_analysis.review_status', review_status)
        if human_review_required is not None:
            query = query.eq('contract_analysis.human_review_required', human_review_required)
        if processing_status:
            if processing_status == 'processing':
                query = query.eq('processed', False)
            elif processing_status == 'completed':
                query = query.eq('processed', True)

        # Order and paginate
        query = query.order('uploaded_at', desc=True).limit(limit).offset(offset)

        result = await asyncio.to_thread(lambda: query.execute())

        # Transform data to match expected format
        contracts = []
        for doc in result.data or []:
            analysis = doc.get('contract_analysis')

            # Handle analysis - can be dict, list, or None
            analysis_data = None
            if analysis:
                # If it's a list with items, take the first one
                if isinstance(analysis, list) and len(analysis) > 0:
                    analysis_data = analysis[0]
                # If it's already a dict with data, use it
                elif isinstance(analysis, dict) and analysis.get('id'):
                    analysis_data = analysis

            # If analysis exists
            if analysis_data:
                # Extract counterparty from parties field if not set
                counterparty_name = doc['counterparty_name']
                if not counterparty_name and analysis_data.get('parties'):
                    try:
                        import json
                        parties = analysis_data.get('parties')
                        if isinstance(parties, str):
                            parties = json.loads(parties)
                        if isinstance(parties, list) and len(parties) > 1:
                            # Use second party as counterparty (first is usually "us")
                            counterparty_name = parties[1]
                    except:
                        pass

                contract = {
                    'id': analysis_data['id'],
                    'document_id': doc['id'],
                    'filename': doc['filename'],
                    'counterparty_name': counterparty_name,
                    'contract_type': analysis_data.get('contract_type') or doc.get('contract_type'),
                    'parties': analysis_data.get('parties'),
                    'effective_date': analysis_data.get('effective_date'),
                    'total_value': analysis_data.get('total_value'),
                    'overall_risk_level': analysis_data.get('overall_risk_level'),
                    'risk_score': analysis_data.get('risk_score'),
                    'human_review_required': analysis_data.get('human_review_required'),
                    'review_status': analysis_data.get('review_status'),
                    'executive_summary': analysis_data.get('executive_summary'),
                    'uploaded_at': doc['uploaded_at'],
                    'created_at': analysis_data.get('created_at'),
                    'processing': False
                }
            else:
                # No analysis yet - check if processing or failed
                processing_status = doc.get('processing_status', 'pending')
                is_error = processing_status.startswith('error:') if processing_status else False
                is_processing = (processing_status == 'pending' or processing_status == 'completed') and not is_error

                contract = {
                    'id': None,
                    'document_id': doc['id'],
                    'filename': doc['filename'],
                    'counterparty_name': doc['counterparty_name'],
                    'contract_type': doc.get('contract_type'),
                    'parties': None,
                    'effective_date': None,
                    'total_value': None,
                    'overall_risk_level': None,
                    'risk_score': None,
                    'human_review_required': None,
                    'review_status': 'failed' if is_error else 'pending',
                    'executive_summary': None,
                    'uploaded_at': doc['uploaded_at'],
                    'created_at': None,
                    'processing': is_processing,
                    'processing_status': processing_status,
                    'error_message': processing_status if is_error else None
                }

            contracts.append(contract)

        return {
            'success': True,
            'contracts': contracts,
            'total': result.count,
            'limit': limit,
            'offset': offset
        }

    except Exception as e:
        import traceback
        logger.error(f"❌ Error listing contracts: {type(e).__name__}: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {str(e)}")


@router.get("/{contract_id}")
async def get_contract_analysis(
    contract_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get detailed contract analysis"""
    try:
        validate_uuid(contract_id, "contract_id")

        # First check if document exists and get processing status
        doc_result = await asyncio.to_thread(
            lambda: supabase.table('documents')
                .select('filename, uploaded_by, processing_status, error_message')
                .eq('id', contract_id)
                .single()
                .execute()
        )

        if not doc_result.data:
            raise HTTPException(status_code=404, detail="Contract not found")

        # Authorization check
        if current_user['role'] != 'admin' and doc_result.data['uploaded_by'] != current_user['id']:
            raise HTTPException(status_code=403, detail="Not authorized to access this contract")

        processing_status = doc_result.data.get('processing_status', 'unknown')

        # If processing failed or is still in progress, return early with status
        if processing_status in ('error', 'pending', 'processing'):
            return {
                'success': False,
                'status': processing_status,
                'message': doc_result.data.get('error_message') if processing_status == 'error' else f'Contract is currently {processing_status}',
                'filename': doc_result.data.get('filename')
            }

        # Try to get analysis (may not exist if processing failed)
        result = await asyncio.to_thread(
            lambda: supabase.table('contract_analysis')
                .select('*, documents!inner(filename, counterparty_name, uploaded_by, uploaded_at, storage_url)')
                .eq('document_id', contract_id)
                .execute()
        )

        if not result.data or len(result.data) == 0:
            # Document exists but no analysis - processing likely failed
            return {
                'success': False,
                'status': 'no_analysis',
                'message': 'Contract analysis is not available. Processing may have failed.',
                'filename': doc_result.data.get('filename'),
                'error_message': doc_result.data.get('error_message')
            }

        analysis = result.data[0]

        # Parse full_analysis JSON string to object
        if 'full_analysis' in analysis and isinstance(analysis['full_analysis'], str):
            try:
                import json
                analysis['full_analysis'] = json.loads(analysis['full_analysis'])
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse full_analysis for contract {contract_id}")
                analysis['full_analysis'] = {}

        return {
            'success': True,
            'analysis': analysis
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching contract analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Contract Review Decision
# ============================================================================

@router.patch("/{contract_id}/review")
async def save_review_decision(
    contract_id: str,
    review_status: str = Query(..., regex="^(approved|approved_with_conditions|negotiation_required|rejected)$"),
    reviewer_notes: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Save human review decision on a contract"""
    try:
        validate_uuid(contract_id, "contract_id")

        # Verify contract exists and user has access
        doc_check = await asyncio.to_thread(
            lambda: supabase.table('documents')
                .select('uploaded_by')
                .eq('id', contract_id)
                .single()
                .execute()
        )

        if not doc_check.data:
            raise HTTPException(status_code=404, detail="Contract not found")

        if current_user['role'] != 'admin' and doc_check.data['uploaded_by'] != current_user['id']:
            raise HTTPException(status_code=403, detail="Not authorized to review this contract")

        # Update contract_analysis record
        update_data = {
            'review_status': review_status,
            'reviewer_notes': reviewer_notes,
            'reviewed_by': current_user['id'],
            'reviewed_at': 'now()'
        }

        result = await asyncio.to_thread(
            lambda: supabase.table('contract_analysis')
                .update(update_data)
                .eq('document_id', contract_id)
                .execute()
        )

        logger.info(f"✅ Review decision saved for contract: {contract_id} - {review_status}")

        return {
            'success': True,
            'message': 'Review decision saved',
            'contract_id': contract_id,
            'review_status': review_status
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error saving review decision: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{contract_id}/feedback")
async def save_team_feedback(
    contract_id: str,
    feedback: dict,
    current_user: dict = Depends(get_current_user)
):
    """Save team feedback on contract analysis quality"""
    try:
        validate_uuid(contract_id, "contract_id")

        # Extract feedback text from request body
        feedback_text = feedback.get('team_feedback', '')

        if not feedback_text or not feedback_text.strip():
            raise HTTPException(status_code=400, detail="Feedback text is required")

        # Verify contract analysis exists
        analysis_check = await asyncio.to_thread(
            lambda: supabase.table('contract_analysis')
                .select('document_id')
                .eq('document_id', contract_id)
                .single()
                .execute()
        )

        if not analysis_check.data:
            raise HTTPException(status_code=404, detail="Contract not found")

        # Check user access via documents table
        doc_check = await asyncio.to_thread(
            lambda: supabase.table('documents')
                .select('uploaded_by')
                .eq('id', contract_id)
                .single()
                .execute()
        )

        if current_user['role'] != 'admin' and doc_check.data['uploaded_by'] != current_user['id']:
            raise HTTPException(status_code=403, detail="Not authorized to provide feedback on this contract")

        # Update contract_analysis record with feedback
        from datetime import datetime, timezone

        update_data = {
            'team_feedback': feedback_text,
            'feedback_submitted_by': current_user['id'],
            'feedback_submitted_at': datetime.now(timezone.utc).isoformat()
        }

        result = await asyncio.to_thread(
            lambda: supabase.table('contract_analysis')
                .update(update_data)
                .eq('document_id', contract_id)
                .execute()
        )

        logger.info(f"✅ Team feedback saved for contract: {contract_id}")

        return {
            'success': True,
            'message': 'Team feedback saved successfully',
            'contract_id': contract_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error saving team feedback: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Contract Chat (Human-in-the-Loop)
# ============================================================================

@router.post("/{contract_id}/chat")
async def contract_chat(
    contract_id: str,
    message: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Chat about a specific contract (human-in-the-loop assistance)
    Provides context-aware responses using contract text and analysis
    """
    try:
        validate_uuid(contract_id, "contract_id")

        # Get contract analysis
        analysis_result = await asyncio.to_thread(
            lambda: supabase.table('contract_analysis')
                .select('*, documents!inner(*)')
                .eq('document_id', contract_id)
                .single()
                .execute()
        )

        if not analysis_result.data:
            raise HTTPException(status_code=404, detail="Contract analysis not found")

        analysis = analysis_result.data

        # Authorization check
        if current_user['role'] != 'admin' and analysis['documents']['uploaded_by'] != current_user['id']:
            raise HTTPException(status_code=403, detail="Not authorized to access this contract")

        # TODO: Implement chat functionality with Claude
        # This would:
        # 1. Retrieve contract text from storage
        # 2. Load previous chat history
        # 3. Send to Claude with contract context + analysis results
        # 4. Store chat message in contract_chat_history table
        # 5. Return response

        return {
            'success': True,
            'message': 'Chat functionality coming soon',
            'contract_id': contract_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in contract chat: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Contract Comparison
# ============================================================================

@router.get("/compare")
async def compare_contracts(
    contract_ids: str = Query(..., description="Comma-separated contract IDs to compare"),
    current_user: dict = Depends(get_current_user)
):
    """Compare multiple contracts side-by-side"""
    try:
        # Parse contract IDs
        ids = [id.strip() for id in contract_ids.split(',')]

        if len(ids) < 2 or len(ids) > 3:
            raise HTTPException(status_code=400, detail="Please provide 2-3 contract IDs to compare")

        # Validate UUIDs
        for contract_id in ids:
            validate_uuid(contract_id, "contract_id")

        # Fetch all analyses
        result = await asyncio.to_thread(
            lambda: supabase.table('contract_analysis')
                .select('*, documents!inner(*)')
                .in_('document_id', ids)
                .execute()
        )

        analyses = result.data

        # Authorization check
        for analysis in analyses:
            if current_user['role'] != 'admin' and analysis['documents']['uploaded_by'] != current_user['id']:
                raise HTTPException(status_code=403, detail=f"Not authorized to access contract: {analysis['document_id']}")

        return {
            'success': True,
            'contracts': analyses,
            'count': len(analyses)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error comparing contracts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Contract Deletion
# ============================================================================

@router.delete("")
async def delete_contracts(
    document_ids: List[str] = Query(..., description="List of document IDs to delete"),
    current_user: dict = Depends(get_current_user)
):
    """Delete one or more contracts (soft delete or hard delete based on permissions)"""
    try:
        # Validate all UUIDs
        for doc_id in document_ids:
            validate_uuid(doc_id, "document_id")

        if not document_ids:
            raise HTTPException(status_code=400, detail="No document IDs provided")

        # Verify user has permission to delete these contracts (get storage_path now)
        docs_check = await asyncio.to_thread(
            lambda: supabase.table('documents')
                .select('id, uploaded_by, filename, storage_path')
                .in_('id', document_ids)
                .execute()
        )

        if not docs_check.data:
            raise HTTPException(status_code=404, detail="No contracts found with provided IDs")

        # Authorization check - user can only delete their own contracts unless admin
        if current_user['role'] != 'admin':
            for doc in docs_check.data:
                if doc['uploaded_by'] != current_user['id']:
                    raise HTTPException(
                        status_code=403,
                        detail=f"Not authorized to delete contract: {doc['filename']}"
                    )

        # Delete files from storage FIRST (before deleting DB records)
        storage_paths = [doc['storage_path'] for doc in docs_check.data if doc.get('storage_path')]
        if storage_paths:
            try:
                await asyncio.to_thread(
                    lambda: supabase.storage.from_('documents').remove(storage_paths)
                )
                logger.info(f"🗑️ Deleted {len(storage_paths)} file(s) from storage")
            except Exception as e:
                logger.warning(f"⚠️ Failed to delete storage files: {str(e)}")
                # Continue even if storage deletion fails

        # Delete contract_analysis records (cascade will happen, but explicit is safer)
        await asyncio.to_thread(
            lambda: supabase.table('contract_analysis')
                .delete()
                .in_('document_id', document_ids)
                .execute()
        )

        # Delete document records
        deleted_result = await asyncio.to_thread(
            lambda: supabase.table('documents')
                .delete()
                .in_('id', document_ids)
                .execute()
        )

        deleted_count = len(docs_check.data)
        logger.info(f"✅ Deleted {deleted_count} contract(s)")

        return {
            'success': True,
            'deleted_count': deleted_count,
            'message': f"Successfully deleted {deleted_count} contract(s)"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting contracts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Performance Metrics
# ============================================================================

@router.get("/dashboard/performance")
async def get_performance_metrics(
    days: int = Query(30, ge=1, le=90),
    current_user: dict = Depends(require_admin)
):
    """
    Get contract processing performance metrics over time

    Returns pages per minute over time to track processing speed improvements
    """
    try:
        # Calculate date range in Python (Supabase client doesn't accept SQL expressions)
        from datetime import datetime, timedelta
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # Query for contracts with performance data from the last N days
        result = await asyncio.to_thread(
            lambda: supabase.from_('contract_analysis')
                .select('created_at, processing_time_seconds, document_id')
                .gte('created_at', start_date.isoformat())
                .not_.is_('processing_time_seconds', 'null')
                .order('created_at', desc=False)
                .execute()
        )

        analyses = result.data or []

        # Get page counts from documents table
        if analyses:
            doc_ids = [a['document_id'] for a in analyses]
            docs_result = await asyncio.to_thread(
                lambda: supabase.from_('documents')
                    .select('id, page_count')
                    .in_('id', doc_ids)
                    .execute()
            )

            # Create lookup map
            page_counts = {doc['id']: doc.get('page_count', 0) for doc in docs_result.data or []}

            # Calculate performance metrics
            metrics = []
            for analysis in analyses:
                doc_id = analysis['document_id']
                page_count = page_counts.get(doc_id, 0) or 0  # Ensure not None
                processing_time_seconds = float(analysis['processing_time_seconds'] or 0)

                if page_count and page_count > 0 and processing_time_seconds > 0:
                    # Calculate pages per minute
                    pages_per_minute = (page_count / processing_time_seconds) * 60

                    metrics.append({
                        'date': analysis['created_at'],
                        'pages_per_minute': round(pages_per_minute, 2),
                        'page_count': page_count,
                        'processing_time_seconds': processing_time_seconds,
                        'document_id': doc_id
                    })
        else:
            metrics = []

        # Calculate aggregate stats
        if metrics:
            pages_per_min_values = [m['pages_per_minute'] for m in metrics]
            avg_pages_per_minute = sum(pages_per_min_values) / len(pages_per_min_values)
            total_pages = sum(m['page_count'] for m in metrics)
            total_time = sum(m['processing_time_seconds'] for m in metrics)
        else:
            avg_pages_per_minute = 0
            total_pages = 0
            total_time = 0

        return {
            'success': True,
            'metrics': metrics,
            'summary': {
                'avg_pages_per_minute': round(avg_pages_per_minute, 2),
                'total_contracts_analyzed': len(metrics),
                'total_pages_processed': total_pages,
                'total_processing_time_seconds': round(total_time, 2),
                'period_days': days
            }
        }

    except Exception as e:
        logger.error(f"❌ Error fetching performance metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{contract_id}/reprocess")
async def reprocess_contract(
    contract_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """
    Reprocess a contract - deletes existing analysis and re-analyzes the document
    Preserves the original created_at timestamp
    """
    try:
        validate_uuid(contract_id, "contract_id")

        # Check if document exists
        doc_result = await asyncio.to_thread(
            lambda: supabase.table('documents')
                .select('id, filename, uploaded_by, created_at')
                .eq('id', contract_id)
                .single()
                .execute()
        )

        if not doc_result.data:
            raise HTTPException(status_code=404, detail="Contract not found")

        # Authorization check
        if current_user['role'] != 'admin' and doc_result.data['uploaded_by'] != current_user['id']:
            raise HTTPException(status_code=403, detail="Not authorized to reprocess this contract")

        filename = doc_result.data['filename']
        original_created_at = doc_result.data.get('created_at')

        logger.info(f"Reprocessing contract: {filename} ({contract_id})")

        # Get existing analysis created_at to preserve it
        analysis_result = await asyncio.to_thread(
            lambda: supabase.table('contract_analysis')
                .select('created_at')
                .eq('document_id', contract_id)
                .execute()
        )

        original_analysis_created_at = None
        if analysis_result.data and len(analysis_result.data) > 0:
            original_analysis_created_at = analysis_result.data[0].get('created_at')

        # Delete existing analysis
        await asyncio.to_thread(
            lambda: supabase.table('contract_analysis')
                .delete()
                .eq('document_id', contract_id)
                .execute()
        )
        logger.info(f"Deleted existing analysis for {filename}")

        # Reset document status
        await asyncio.to_thread(
            lambda: supabase.table('documents').update({
                'processing_status': 'pending',
                'error_message': None
            }).eq('id', contract_id).execute()
        )
        logger.info(f"Reset document status to pending for {filename}")

        # Process contract in background
        async def reprocess_and_restore_timestamp():
            """Process contract and restore original timestamp"""
            try:
                await process_contract(contract_id)
                
                # Restore original analysis created_at timestamp if it existed
                if original_analysis_created_at:
                    await asyncio.to_thread(
                        lambda: supabase.table('contract_analysis').update({
                            'created_at': original_analysis_created_at
                        }).eq('document_id', contract_id).execute()
                    )
                    logger.info(f"Restored original timestamp for {filename}")
                
                logger.info(f"✅ Reprocessing complete for {filename}")
            except Exception as e:
                logger.error(f"❌ Reprocessing failed for {filename}: {e}")

        background_tasks.add_task(reprocess_and_restore_timestamp)

        return {
            'success': True,
            'message': f'Reprocessing started for {filename}',
            'contract_id': contract_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error initiating reprocess: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
