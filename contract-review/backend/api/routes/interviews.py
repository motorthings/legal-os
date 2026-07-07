"""
Voice interview and Solomon extraction routes
Handles ElevenLabs integration, webhooks, and extraction management
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List
import asyncio
import hmac
import hashlib
import os
from datetime import datetime

from auth import get_current_user, require_admin
from database import get_supabase
# from services import (
#     create_interview_session, handle_interview_completion,
#     get_interview_status, extract_interview_data, retry_extraction
# )  # These functions don't exist
# from services.quick_prompts_generator import generate_quick_prompts  # Module doesn't exist
from validation import validate_uuid
from logger_config import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["interviews"])
supabase = get_supabase()


class StartInterviewRequest(BaseModel):
    user_id: str
    admin_notes: Optional[str] = None


class ExtractionUpdateRequest(BaseModel):
    status: str  # pending, approved, rejected


# ============================================================================
# Interview Management
# ============================================================================

@router.post("/api/onboarding/start-interview")
async def start_interview(
    request: StartInterviewRequest,
    current_user: dict = Depends(require_admin)
):
    """Start a new interview session (admin only)"""
    try:
        validate_uuid(request.user_id, "user_id")

        # Get user details from database including client_id
        user_result = await asyncio.to_thread(
            lambda: supabase.table('users')\
                .select('email, name, client_id, clients(name)')\
                .eq('id', request.user_id)\
                .single()\
                .execute()
        )

        if not user_result.data:
            raise HTTPException(status_code=404, detail="User not found")

        user_data = user_result.data

        # Create session using service with user's client_id
        session_data = await create_interview_session(
            client_id=user_data.get('client_id'),  # Use user's client_id from database
            user_id=request.user_id,
            client_name=user_data.get('name', 'User'),
            client_email=user_data.get('email', ''),
            organization_name=user_data.get('clients', {}).get('name') if user_data.get('clients') else None
        )

        logger.info(f"✅ Session created: {session_data}")

        response = {
            'success': True,
            **session_data
        }

        logger.info(f"📤 Returning response: {response}")

        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Start interview error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/webhooks/interview-complete")
async def interview_complete_webhook(request: Request):
    """Handle ElevenLabs interview completion webhook"""
    try:
        # Get raw body for signature verification
        body = await request.body()

        # Check for test mode (development only)
        test_mode = request.headers.get('X-Test-Mode') == 'true'
        is_dev = os.getenv('ENVIRONMENT', 'production') == 'development'

        # Verify webhook signature (skip in test mode during development)
        if not (test_mode and is_dev):
            signature = request.headers.get('ElevenLabs-Signature', '')
            timestamp = request.headers.get('ElevenLabs-Timestamp', '')
            secret = os.getenv('ELEVENLABS_WEBHOOK_SECRET', '')

            if secret:
                signed_payload = f"{timestamp}.{body.decode('utf-8')}"
                expected_signature = hmac.new(
                    secret.encode('utf-8'),
                    signed_payload.encode('utf-8'),
                    hashlib.sha256
                ).hexdigest()

                if not hmac.compare_digest(expected_signature, signature.replace('sha256=', '')):
                    raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Parse JSON
        import json
        payload = json.loads(body)
        
        # Handle completion
        result = handle_interview_completion(payload)
        
        return {
            'success': True,
            'message': 'Webhook processed',
            **result
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Webhook error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/test/inject-interview")
async def inject_test_interview(
    request: Request,
    current_user: dict = Depends(require_admin)
):
    """
    Test endpoint to inject synthetic interview (admin only)
    Bypasses webhook signature verification for testing
    """
    try:
        body = await request.json()

        # Call handle_interview_completion directly
        result = await handle_interview_completion(
            agent_id=body.get('agent_id'),
            conversation_id=body.get('conversation_id'),
            transcript_data=body.get('transcript')
        )

        return {
            'success': True,
            'message': 'Test interview injected',
            **result
        }
    except Exception as e:
        logger.error(f"❌ Test injection error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/interview-status/{user_id}")
async def get_interview_status_endpoint(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get interview status for a user"""
    try:
        validate_uuid(user_id, "user_id")

        # Users can only check their own status (unless admin)
        if current_user['role'] != 'admin' and current_user['id'] != user_id:
            raise HTTPException(status_code=403, detail="Not authorized")

        # Await the async function
        status = await get_interview_status(user_id)
        return {
            'success': True,
            **status
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Get status error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/interview-session/{session_id}")
async def get_interview_session(
    session_id: str
):
    """Get public interview session details (no auth required for interview page)"""
    try:
        # session_id is a string like "session_abc123", not a UUID
        # Don't validate as UUID - query by session_id column instead

        result = await asyncio.to_thread(
            lambda: supabase.table('interview_sessions')\
                .select('*')\
                .eq('session_id', session_id)\
                .single()\
                .execute()
        )

        if not result.data:
            raise HTTPException(status_code=404, detail="Session not found")

        return {
            'success': True,
            'session': result.data
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Get session error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Extraction Management (Solomon Review)
# ============================================================================

@router.get("/api/extractions")
async def list_extractions(
    current_user: dict = Depends(require_admin),
    status: Optional[str] = None,
    limit: int = 200
):
    """List all interview extractions (admin only)"""
    try:
        # Join with clients and solomon_reviews to get review data
        query = supabase.table('interview_extractions').select('''
            *,
            clients(name),
            solomon_reviews(
                id,
                status,
                reviewed_at,
                reviewed_by,
                deployed_at,
                deployment_notes
            )
        ''')

        if status:
            query = query.eq('status', status)

        result = await asyncio.to_thread(
            lambda: query.order('created_at', desc=True).limit(limit).execute()
        )

        # Get all unique client IDs and reviewer IDs
        client_ids = set()
        reviewer_ids = set()
        for item in result.data or []:
            if item.get('client_id'):
                client_ids.add(item.get('client_id'))
            reviews = item.get('solomon_reviews') or []
            review = reviews[0] if reviews else None
            if review and review.get('reviewed_by'):
                reviewer_ids.add(review.get('reviewed_by'))

        # Fetch user names by client_id (to show user names instead of company names)
        user_by_client = {}
        if client_ids:
            users_by_client_result = await asyncio.to_thread(
                lambda: supabase.table('users')\
                    .select('id, name, client_id')\
                    .in_('client_id', list(client_ids))\
                    .execute()
            )
            # Map client_id to first user's name for that client
            for user in users_by_client_result.data or []:
                cid = user.get('client_id')
                if cid and cid not in user_by_client:
                    user_by_client[cid] = user.get('name', 'Unknown')

        # Fetch reviewer names in one query
        reviewer_map = {}
        if reviewer_ids:
            users_result = await asyncio.to_thread(
                lambda: supabase.table('users')\
                    .select('id, name')\
                    .in_('id', list(reviewer_ids))\
                    .execute()
            )
            reviewer_map = {user['id']: user['name'] for user in users_result.data or []}

        # Transform data to match frontend interface
        extractions = []
        for item in result.data or []:
            # Get user name from client_id mapping, fall back to client name
            client_id = item.get('client_id') or ''
            user_name = user_by_client.get(client_id)
            if not user_name:
                # Fall back to client name if no user found
                clients_data = item.get('clients')
                user_name = clients_data.get('name', 'Unknown') if clients_data else 'Unknown'

            # Get review data - handle None case
            reviews = item.get('solomon_reviews') or []
            review = reviews[0] if reviews else None

            # Get reviewer name from map
            reviewer_name = ''
            if review and review.get('reviewed_by'):
                reviewer_name = reviewer_map.get(review.get('reviewed_by'), '')

            extractions.append({
                'id': item['id'],
                'client_id': client_id,
                'user_name': user_name,
                'transcript_preview': item.get('transcript', '')[:200] + '...' if item.get('transcript') else '',
                'extraction_json': item.get('extraction_json') or {},
                'status': item.get('status') or 'unknown',
                'deployment_status': review.get('status', 'not_generated') if review else 'not_generated',
                'completeness_score': item.get('completeness_score') or 0,
                'created_at': item.get('created_at') or '',
                'processed_at': item.get('processed_at') or '',
                'reviewed_at': review.get('reviewed_at', '') if review else '',
                'reviewed_by': reviewer_name or '',
                'deployed_at': review.get('deployed_at', '') if review else '',
                'interview_session_id': item.get('interview_session_id') or '',
                'error_message': item.get('error_message') or '',
                'review_reason': item.get('review_reason') or ''
            })

        return {
            'success': True,
            'data': extractions,
            'total': len(extractions)
        }
    except Exception as e:
        logger.error(f"❌ List extractions error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/extractions/{extraction_id}")
async def get_extraction(
    extraction_id: str,
    current_user: dict = Depends(require_admin)
):
    """Get detailed extraction data (admin only)"""
    try:
        validate_uuid(extraction_id, "extraction_id")

        result = await asyncio.to_thread(
            lambda: supabase.table('interview_extractions')\
                .select('''
                    *,
                    clients!interview_extractions_client_id_fkey(id, name, status),
                    interview_sessions(
                        id,
                        agent_id,
                        session_id,
                        session_url,
                        status,
                        created_at,
                        completed_at,
                        metadata
                    ),
                    solomon_reviews(
                        id,
                        status,
                        generated_instructions,
                        reviewed_at,
                        reviewed_by,
                        deployment_notes,
                        deployed_at,
                        created_at,
                        metadata
                    )
                ''')\
                .eq('id', extraction_id)\
                .single()\
                .execute()
        )

        # Get user_id from client_id (limit to 1 in case of duplicates)
        user_result = await asyncio.to_thread(
            lambda: supabase.table('users')\
                .select('id')\
                .eq('client_id', result.data['client_id'])\
                .order('created_at', desc=False)\
                .limit(1)\
                .execute()
        )

        if not result.data:
            raise HTTPException(status_code=404, detail="Extraction not found")

        # Transform to match frontend interface
        data = result.data
        reviews = data.get('solomon_reviews', [])
        review = reviews[0] if reviews else None

        # interview_sessions is a single object (many-to-one FK), not an array
        interview_session = data.get('interview_sessions')

        extraction = {
            'id': data['id'],
            'client_id': data.get('client_id'),
            'user_id': user_result.data[0]['id'] if user_result.data else None,  # Get user_id from users table
            'client': data.get('clients', {}),
            'transcript': data.get('transcript', ''),
            'audio_url': data.get('audio_url'),
            'extraction_json': data.get('extraction_json', {}),
            'status': data.get('status'),
            'completeness_score': data.get('completeness_score'),
            'created_at': data.get('created_at'),
            'processed_at': data.get('processed_at'),
            'error_message': data.get('error_message'),
            'review_reason': data.get('review_reason'),
            'interview_session': interview_session,
            'review': {
                'id': review.get('id') if review else None,
                'status': review.get('status', 'not_generated') if review else 'not_generated',
                'generated_instructions': review.get('generated_instructions') if review else None,
                'reviewed_at': review.get('reviewed_at') if review else None,
                'reviewed_by': review.get('reviewed_by') if review else None,
                'deployment_notes': review.get('deployment_notes') if review else None,
                'deployed_at': review.get('deployed_at') if review else None,
                'created_at': review.get('created_at') if review else None,
            }
        }

        return {
            'success': True,
            'extraction': extraction
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Get extraction error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/api/extractions/{extraction_id}")
async def update_extraction(
    extraction_id: str,
    request: ExtractionUpdateRequest,
    current_user: dict = Depends(require_admin)
):
    """Update extraction status (admin only)"""
    try:
        validate_uuid(extraction_id, "extraction_id")
        
        result = await asyncio.to_thread(
            lambda: supabase.table('interview_extractions')\
                .update({'status': request.status})\
                .eq('id', extraction_id)\
                .execute()
        )
        
        return {
            'success': True,
            'extraction': result.data[0] if result.data else None
        }
    except Exception as e:
        logger.error(f"❌ Update extraction error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/extractions/{extraction_id}/regenerate")
async def regenerate_extraction(
    extraction_id: str,
    current_user: dict = Depends(require_admin)
):
    """Regenerate system instructions for an extraction"""
    try:
        validate_uuid(extraction_id, "extraction_id")
        
        result = retry_extraction(extraction_id)
        
        return {
            'success': True,
            **result
        }
    except Exception as e:
        logger.error(f"❌ Regenerate error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/extractions/{extraction_id}/approve")
async def approve_extraction(
    extraction_id: str,
    current_user: dict = Depends(require_admin)
):
    """Approve and deploy extraction to user's system instructions"""
    try:
        validate_uuid(extraction_id, "extraction_id")
        
        # Get extraction
        extraction_result = await asyncio.to_thread(
            lambda: supabase.table('interview_extractions')\
                .select('*')\
                .eq('id', extraction_id)\
                .single()\
                .execute()
        )

        if not extraction_result.data:
            raise HTTPException(status_code=404, detail="Extraction not found")

        extraction = extraction_result.data

        # Get user_id from client_id (limit to 1 in case of duplicates)
        user_result = await asyncio.to_thread(
            lambda: supabase.table('users')\
                .select('id, name, email')\
                .eq('client_id', extraction['client_id'])\
                .order('created_at', desc=False)\
                .limit(1)\
                .execute()
        )

        if not user_result.data:
            raise HTTPException(status_code=404, detail="User not found for client")

        user_id = user_result.data[0]['id']
        
        # Update user's system instructions
        if extraction.get('generated_instructions'):
            await asyncio.to_thread(
                lambda: supabase.table('users')\
                    .update({'system_instructions': extraction['generated_instructions']})\
                    .eq('id', user_id)\
                    .execute()
            )
        
        # Mark as approved
        await asyncio.to_thread(
            lambda: supabase.table('interview_extractions')\
                .update({
                    'status': 'approved',
                    'approved_by': current_user['id'],
                    'approved_at': datetime.utcnow().isoformat()
                })\
                .eq('id', extraction_id)\
                .execute()
        )

        # Update solomon_reviews status to deployed
        await asyncio.to_thread(
            lambda: supabase.table('solomon_reviews')\
                .update({
                    'status': 'deployed',
                    'reviewed_by': current_user['id'],
                    'reviewed_at': datetime.utcnow().isoformat(),
                    'deployed_at': datetime.utcnow().isoformat()
                })\
                .eq('extraction_id', extraction_id)\
                .execute()
        )

        # Auto-generate quick prompts based on selected functions
        try:
            extraction_json = extraction.get('extraction_json', {})
            selected_functions = extraction_json.get('selected_functions', [])

            if not selected_functions:
                # Fallback: use all 10 functions
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

            # User context already fetched above
            user_context = {
                'name': user_result.data[0].get('name'),
                'email': user_result.data[0].get('email')
            }

            # Generate prompts
            prompts = generate_quick_prompts(
                selected_functions=selected_functions,
                max_prompts=7,
                user_context=user_context
            )

            # Delete existing auto-generated prompts
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
                        'generated_at': 'deployment',
                        'extraction_id': extraction_id
                    }
                }
                for prompt in prompts
            ]

            await asyncio.to_thread(
                lambda: supabase.table('user_prompts')\
                    .insert(prompt_records)\
                    .execute()
            )

            logger.info(f"✅ Generated {len(prompts)} quick prompts for user {user_id}")
        except Exception as prompt_error:
            # Log error but don't fail the approval
            logger.warning(f"⚠️ Failed to generate quick prompts: {str(prompt_error)}")

        return {
            'success': True,
            'message': 'Extraction approved and deployed'
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Approve error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/extractions/{extraction_id}/reject")
async def reject_extraction(
    extraction_id: str,
    current_user: dict = Depends(require_admin)
):
    """Reject an extraction"""
    try:
        validate_uuid(extraction_id, "extraction_id")
        
        await asyncio.to_thread(
            lambda: supabase.table('interview_extractions')\
                .update({'status': 'rejected'})\
                .eq('id', extraction_id)\
                .execute()
        )
        
        return {
            'success': True,
            'message': 'Extraction rejected'
        }
    except Exception as e:
        logger.error(f"❌ Reject error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
