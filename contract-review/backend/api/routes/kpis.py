"""
KPI endpoint routes
Handles dashboard KPI metrics for Bradbury Impact Loop-aligned measurements
"""
from fastapi import APIRouter, Depends, Request, HTTPException
from slowapi import Limiter
from slowapi.util import get_remote_address
from logger_config import get_logger
from auth import get_current_user
from database import get_supabase
from typing import Optional, List, Dict, Any, Set
from datetime import datetime, timedelta
from pydantic import BaseModel
from collections import defaultdict

logger = get_logger(__name__)
router = APIRouter(prefix="/api/kpis", tags=["kpis"])
limiter = Limiter(key_func=get_remote_address)
supabase = get_supabase()

# Strategic work keywords for Ideation Velocity detection
# These indicate high-value, knowledge-application work aligned with Bradbury Impact Loop Tier 7
STRATEGIC_KEYWORDS = [
    # Document creation
    'draft', 'write', 'compose', 'create', 'prepare',
    # Strategic planning
    'strategy', 'strategic', 'plan', 'planning', 'roadmap',
    # Analysis and frameworks
    'framework', 'analyze', 'analysis', 'evaluate', 'assessment',
    # Business deliverables
    'proposal', 'report', 'presentation', 'brief', 'memo',
    'executive summary', 'business case', 'pitch',
    # Decision support
    'recommend', 'recommendation', 'options', 'approach',
    # Communication
    'email to', 'message to', 'response to', 'reply to',
    # Project work
    'project', 'initiative', 'campaign', 'launch'
]


def is_strategic_message(content: str) -> bool:
    """
    Detect if a message indicates strategic work intent

    Args:
        content: The user's first message in a conversation

    Returns:
        True if the message appears to be strategic work, False otherwise
    """
    content_lower = content.lower()
    return any(keyword in content_lower for keyword in STRATEGIC_KEYWORDS)


class IdeationVelocityResponse(BaseModel):
    """Response model for Ideation Velocity KPI"""
    user_id: str
    time_period: str  # 'week', 'month', 'all_time'
    drafts_initiated: int  # Strategic conversations only
    total_conversations: int  # All conversations for context
    strategic_ratio: float  # Percentage of strategic work
    trend_data: List[Dict[str, Any]]  # [{week: '2025-W46', count: 5, strategic: 3}, ...]
    avg_per_week: float


class CorrectionLoopResponse(BaseModel):
    """Response model for Correction Loop KPI"""
    user_id: str
    avg_turns_to_completion: float
    avg_turns_to_useable_output: float  # More accurate: turns until value delivered
    total_completed_conversations: int
    conversations_with_useable_output: int  # Conversations where useable output was detected
    distribution: Dict[str, int]  # {'1_turn': 10, '2_turns': 25, '3_turns': 15, ...}
    goal_status: str  # 'met' (< 2 avg), 'close' (2-3 avg), 'needs_improvement' (> 3 avg)
    detection_coverage: float  # Percentage of conversations with useable output detection


@router.get("/ideation-velocity")
@limiter.limit("30/minute")
async def get_ideation_velocity(
    request: Request,
    current_user: dict = Depends(get_current_user),
    time_period: str = 'month',  # 'week', 'month', 'all_time'
    user_id: Optional[str] = None  # Optional: for admins to view other users' data
):
    """
    Get Ideation Velocity KPI - Drafts Initiated per Week

    Measures how often the user initiates new strategic work using AI.
    Bradbury Impact Loop Tier 7: Knowledge Application.

    **Query Parameters:**
    - time_period: 'week', 'month', or 'all_time' (default: 'month')

    **Returns:**
    - drafts_initiated: Total drafts in period
    - trend_data: Week-by-week breakdown
    - avg_per_week: Average drafts per week
    """
    # Determine which user to query
    # If user_id provided: show that user's data
    # If no user_id: aggregate ALL users' data
    target_user_id = user_id  # Can be None for "all users"

    logger.info(
        "Ideation Velocity request",
        extra={
            "user_id": current_user['id'],
            "target_user_id": target_user_id or "all_users",
            "time_period": time_period
        }
    )

    try:
        # Calculate date range
        now = datetime.utcnow()
        if time_period == 'week':
            start_date = now - timedelta(days=7)
        elif time_period == 'month':
            start_date = now - timedelta(days=30)
        else:  # all_time
            start_date = datetime(2020, 1, 1)  # Far enough back to get all data

        # Try to use RPC function if it exists and user has client_id
        use_fallback = False
        result = None

        # Get client_id for the target user
        if user_id:
            # Admin is querying another user - get that user's client_id
            target_user_result = supabase.table('users').select('client_id').eq('id', user_id).execute()
            client_id = target_user_result.data[0].get('client_id') if target_user_result.data else None
        else:
            client_id = current_user.get('client_id')

        if client_id:
            try:
                result = supabase.rpc(
                    'get_ideation_velocity',
                    {
                        'p_client_id': client_id,
                        'p_start_date': start_date.isoformat(),
                        'p_end_date': now.isoformat()
                    }
                ).execute()

                if not result.data:
                    use_fallback = True
            except Exception as rpc_error:
                # RPC function doesn't exist or failed, use fallback
                logger.warning(f"RPC get_ideation_velocity failed: {str(rpc_error)}, using fallback query")
                use_fallback = True
        else:
            # No client_id, use fallback query
            logger.info("No client_id found, using fallback query")
            use_fallback = True

        if use_fallback:
            # If RPC doesn't exist, use fallback query with strategic keyword filtering
            logger.info("Using strategic keyword filtering for Ideation Velocity")

            # Get all conversations in the time period
            query = supabase.table('conversations').select('id, created_at')

            # Filter by user_id only if a specific user is selected
            if target_user_id:
                query = query.eq('user_id', target_user_id)

            user_convs_result = query.gte(
                'created_at', start_date.isoformat()
            ).execute()

            if not user_convs_result.data:
                # No conversations
                return {
                    'user_id': target_user_id or 'all_users',
                    'time_period': time_period,
                    'drafts_initiated': 0,
                    'total_conversations': 0,
                    'strategic_ratio': 0.0,
                    'trend_data': [],
                    'avg_per_week': 0.0
                }

            # Get first messages for all conversations to detect strategic intent
            conversation_ids = [conv['id'] for conv in user_convs_result.data]

            # Fetch first user message for each conversation (batch query)
            first_messages_result = supabase.table('messages').select(
                'id, conversation_id, content, timestamp'
            ).in_('conversation_id', conversation_ids).eq(
                'role', 'user'
            ).order('timestamp', desc=False).execute()

            # Group by conversation and get first message
            first_message_by_conv = {}
            for msg in first_messages_result.data:
                conv_id = msg['conversation_id']
                if conv_id not in first_message_by_conv:
                    first_message_by_conv[conv_id] = msg['content']

            # Group conversations by week, tracking strategic vs total
            conversations_by_week: Dict[str, Dict[str, int]] = {}
            strategic_count = 0
            total_count = len(user_convs_result.data)

            for conv in user_convs_result.data:
                created = datetime.fromisoformat(conv['created_at'].replace('Z', '+00:00'))
                week_key = created.strftime('%Y-W%U')

                if week_key not in conversations_by_week:
                    conversations_by_week[week_key] = {'total': 0, 'strategic': 0}

                conversations_by_week[week_key]['total'] += 1

                # Check if first message indicates strategic work
                first_msg = first_message_by_conv.get(conv['id'], '')
                if is_strategic_message(first_msg):
                    conversations_by_week[week_key]['strategic'] += 1
                    strategic_count += 1

            # Build trend data with both total and strategic counts
            trend_data = [
                {
                    'week': week,
                    'count': data['total'],
                    'strategic': data['strategic']
                }
                for week, data in sorted(conversations_by_week.items())
            ]

            # Ideation Velocity = strategic conversations only
            total_drafts = strategic_count
            num_weeks = max(len(trend_data), 1)
            avg_per_week = total_drafts / num_weeks
            strategic_ratio = (strategic_count / total_count * 100) if total_count > 0 else 0.0

        else:
            # Use RPC results (legacy - may not have strategic breakdown)
            trend_data = result.data
            total_drafts = sum(item.get('strategic', item.get('count', 0)) for item in trend_data)
            total_count = sum(item.get('count', 0) for item in trend_data)
            num_weeks = max(len(trend_data), 1)
            avg_per_week = total_drafts / num_weeks
            strategic_ratio = (total_drafts / total_count * 100) if total_count > 0 else 0.0

        logger.info(
            f"Ideation Velocity calculated: {total_drafts} strategic drafts "
            f"({strategic_ratio:.1f}% of {total_count} total), {avg_per_week:.1f} avg/week"
        )

        return {
            'user_id': target_user_id or 'all_users',
            'time_period': time_period,
            'drafts_initiated': total_drafts,
            'total_conversations': total_count,
            'strategic_ratio': round(strategic_ratio, 1),
            'trend_data': trend_data,
            'avg_per_week': round(avg_per_week, 2)
        }

    except Exception as e:
        logger.exception("Error calculating Ideation Velocity", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/correction-loop")
@limiter.limit("30/minute")
async def get_correction_loop(
    request: Request,
    current_user: dict = Depends(get_current_user),
    user_id: Optional[str] = None  # Optional: for admins to view other users' data
):
    """
    Get Correction Loop KPI - Average Turns to Completion

    Measures system effectiveness: How many back-and-forth exchanges
    before usable output? Goal: < 2 turns average.

    **Query Parameters:**
    - user_id: Optional user ID to query (for admins)

    **Returns:**
    - avg_turns_to_completion: Average user turns per conversation
    - total_completed_conversations: Number of conversations analyzed
    - distribution: Breakdown by turn count
    - goal_status: Whether meeting < 2 turn goal
    """
    # Determine which user to query
    # If user_id provided: show that user's data
    # If no user_id: aggregate ALL users' data
    target_user_id = user_id  # Can be None for "all users"

    logger.info(
        "Correction Loop request",
        extra={
            "user_id": current_user['id'],
            "target_user_id": target_user_id or "all_users"
        }
    )

    try:
        # Query conversations including useable output detection fields
        query = supabase.table('conversations').select(
            'id, created_at, updated_at, turns_to_useable_output, '
            'useable_output_message_id, useable_output_method'
        )

        # Filter by user_id only if a specific user is selected
        if target_user_id:
            query = query.eq('user_id', target_user_id)

        conversations_result = query.execute()

        if not conversations_result.data:
            return {
                'user_id': target_user_id or 'all_users',
                'avg_turns_to_completion': 0,
                'avg_turns_to_useable_output': 0,
                'total_completed_conversations': 0,
                'conversations_with_useable_output': 0,
                'distribution': {},
                'goal_status': 'no_data',
                'detection_coverage': 0.0
            }

        # Track both total turns and useable output turns
        turn_counts = []  # Total turns per conversation
        useable_output_turns = []  # Turns to useable output (when detected)
        distribution = {}
        conversations_with_detection = 0

        # FIX: Fetch all messages in a single query instead of N+1 queries
        # Get all conversation IDs
        conversation_ids = [conv['id'] for conv in conversations_result.data]

        if not conversation_ids:
            return {
                'user_id': target_user_id or 'all_users',
                'avg_turns_to_completion': 0,
                'avg_turns_to_useable_output': 0,
                'total_completed_conversations': 0,
                'conversations_with_useable_output': 0,
                'distribution': {},
                'goal_status': 'no_data',
                'detection_coverage': 0.0
            }

        # Single query to fetch all messages for all conversations
        all_messages_result = supabase.table('messages').select(
            'id, conversation_id, role'
        ).in_('conversation_id', conversation_ids).execute()

        # Group messages by conversation_id in memory
        messages_by_conv = defaultdict(list)
        for msg in all_messages_result.data:
            messages_by_conv[msg['conversation_id']].append(msg)

        # Process each conversation using the grouped messages
        for conv in conversations_result.data:
            messages = messages_by_conv.get(conv['id'], [])

            # Count user messages (each is a "turn")
            user_messages = [m for m in messages if m['role'] == 'user']
            num_turns = len(user_messages)

            if num_turns > 0:
                turn_counts.append(num_turns)

                # Update distribution based on useable output turns if available
                # Otherwise fall back to total turns
                turns_for_distribution = conv.get('turns_to_useable_output') or num_turns

                key = f'{turns_for_distribution}_turn{"s" if turns_for_distribution != 1 else ""}'
                distribution[key] = distribution.get(key, 0) + 1

                # Track useable output detection
                if conv.get('useable_output_message_id'):
                    conversations_with_detection += 1
                    if conv.get('turns_to_useable_output'):
                        useable_output_turns.append(conv['turns_to_useable_output'])

        if not turn_counts:
            return {
                'user_id': target_user_id or 'all_users',
                'avg_turns_to_completion': 0,
                'avg_turns_to_useable_output': 0,
                'total_completed_conversations': 0,
                'conversations_with_useable_output': 0,
                'distribution': {},
                'goal_status': 'no_data',
                'detection_coverage': 0.0
            }

        # Calculate averages
        avg_turns = sum(turn_counts) / len(turn_counts)

        # Use useable output turns if we have enough data, otherwise fall back to total turns
        if useable_output_turns:
            avg_useable_output_turns = sum(useable_output_turns) / len(useable_output_turns)
        else:
            avg_useable_output_turns = avg_turns  # Fallback

        detection_coverage = (conversations_with_detection / len(turn_counts) * 100) if turn_counts else 0.0

        # Determine goal status based on useable output turns (more accurate)
        # Fall back to total turns if useable output detection isn't available yet
        metric_for_goal = avg_useable_output_turns if useable_output_turns else avg_turns

        if metric_for_goal < 2:
            goal_status = 'met'
        elif metric_for_goal <= 3:
            goal_status = 'close'
        else:
            goal_status = 'needs_improvement'

        # Calculate trend data (avg turns per week)
        conversations_by_week: Dict[str, Dict[str, list]] = {}
        for conv in conversations_result.data:
            created = datetime.fromisoformat(conv['created_at'].replace('Z', '+00:00'))
            week_key = created.strftime('%Y-W%U')

            if week_key not in conversations_by_week:
                conversations_by_week[week_key] = {'total': [], 'useable': []}

            # Get turns for this conversation
            messages = messages_by_conv.get(conv['id'], [])
            user_messages = [m for m in messages if m['role'] == 'user']
            num_turns = len(user_messages)

            if num_turns > 0:
                conversations_by_week[week_key]['total'].append(num_turns)

                # Track useable output turns if available
                if conv.get('turns_to_useable_output'):
                    conversations_by_week[week_key]['useable'].append(
                        conv['turns_to_useable_output']
                    )

        # Build trend data
        trend_data = []
        for week in sorted(conversations_by_week.keys()):
            week_data = conversations_by_week[week]
            total_list = week_data['total']
            useable_list = week_data['useable']

            if total_list:
                week_avg_total = sum(total_list) / len(total_list)
                week_avg_useable = sum(useable_list) / len(useable_list) if useable_list else None

                trend_entry = {
                    'week': week,
                    'avg_turns': round(week_avg_total, 2),
                    'conversation_count': len(total_list)
                }

                if week_avg_useable is not None:
                    trend_entry['avg_turns_to_useable'] = round(week_avg_useable, 2)
                    trend_entry['useable_count'] = len(useable_list)

                trend_data.append(trend_entry)

        logger.info(
            f"Correction Loop calculated: {avg_turns:.1f} avg total turns, "
            f"{avg_useable_output_turns:.1f} avg to useable output, "
            f"{conversations_with_detection} with detection, status: {goal_status}"
        )

        return {
            'user_id': target_user_id or 'all_users',
            'avg_turns_to_completion': round(avg_turns, 2),
            'avg_turns_to_useable_output': round(avg_useable_output_turns, 2),
            'total_completed_conversations': len(turn_counts),
            'conversations_with_useable_output': conversations_with_detection,
            'distribution': distribution,
            'goal_status': goal_status,
            'detection_coverage': round(detection_coverage, 1),
            'trend_data': trend_data
        }

    except Exception as e:
        logger.exception("Error calculating Correction Loop", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
@limiter.limit("30/minute")
async def get_kpi_summary(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    Get summary of all Bradbury Impact Loop-aligned KPIs

    **Returns:**
    - ideation_velocity: Drafts per week
    - correction_loop: Avg turns to completion
    - impact_focus: Whether meeting behavior change goals
    """
    logger.info("KPI summary request", extra={"user_id": current_user['id']})

    try:
        # Call both KPI endpoints
        ideation = await get_ideation_velocity(request, current_user, 'month')
        correction = await get_correction_loop(request, current_user)

        return {
            'ideation_velocity': {
                'drafts_per_week': ideation['avg_per_week'],
                'total_drafts': ideation['drafts_initiated'],
                'total_conversations': ideation.get('total_conversations', ideation['drafts_initiated']),
                'strategic_ratio': ideation.get('strategic_ratio', 100.0),
                'status': 'good' if ideation['avg_per_week'] >= 2 else 'needs_improvement'
            },
            'correction_loop': {
                'avg_turns': correction['avg_turns_to_completion'],
                'avg_turns_to_useable': correction.get('avg_turns_to_useable_output', correction['avg_turns_to_completion']),
                'detection_coverage': correction.get('detection_coverage', 0.0),
                'status': correction['goal_status']
            },
            'overall_health': {
                'status': 'healthy' if (
                    ideation['avg_per_week'] >= 2 and correction['goal_status'] == 'met'
                ) else 'monitor'
            }
        }

    except Exception as e:
        logger.exception("Error generating KPI summary", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


class CopyEventRequest(BaseModel):
    """Request model for copy event tracking"""
    message_id: str
    content_length: int  # Length of copied content


@router.post("/copy-event/{conversation_id}")
@limiter.limit("60/minute")
async def track_copy_event(
    request: Request,
    conversation_id: str,
    copy_request: CopyEventRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Track when a user copies content from an assistant message

    This is a high-confidence signal that the output was useful.
    Used by the Bradbury Impact Loop to detect useable output.

    **Path Parameters:**
    - conversation_id: The conversation containing the copied message

    **Request Body:**
    - message_id: ID of the message that was copied from
    - content_length: Length of the copied content

    **Returns:**
    - success: Whether the event was tracked
    - useable_output_marked: Whether this triggered useable output detection
    """
    from services.useable_output_detector import mark_useable_output

    logger.info(
        "Copy event received",
        extra={
            "user_id": current_user['id'],
            "conversation_id": conversation_id,
            "message_id": copy_request.message_id,
            "content_length": copy_request.content_length
        }
    )

    try:
        # Only count significant copies (more than 50 chars)
        if copy_request.content_length < 50:
            return {
                'success': True,
                'useable_output_marked': False,
                'reason': 'Content too short to indicate useable output'
            }

        # Mark this message as useable output
        marked = mark_useable_output(
            conversation_id=conversation_id,
            message_id=copy_request.message_id,
            method='copy_event',
            user_id=current_user['id']
        )

        return {
            'success': True,
            'useable_output_marked': marked
        }

    except Exception as e:
        logger.exception("Error tracking copy event", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trips-analysis")
@limiter.limit("30/minute")
async def get_trips_analysis(
    request: Request,
    current_user: dict = Depends(get_current_user),
    user_id: Optional[str] = None
):
    """
    Get TRIPS (Time, Repetition, Importance, Pain, Data) analysis

    Surfaces pain points identified during onboarding interviews
    to track whether the assistant is addressing high-priority areas.

    **Query Parameters:**
    - user_id: Optional user ID to query (for admins)

    **Returns:**
    - pain_points: List of identified pain points with TRIPS scores
    - top_priorities: Top 3 pain points by composite score
    - coverage: How many high-priority areas are being addressed
    """
    target_user_id = user_id or current_user['id']

    logger.info(
        "TRIPS analysis request",
        extra={
            "user_id": current_user['id'],
            "target_user_id": target_user_id
        }
    )

    try:
        # Get interview extractions for the user
        extractions_result = supabase.table('interview_extractions').select(
            'id, extraction_json, completeness_score, created_at'
        ).eq('user_id', target_user_id).order(
            'created_at', desc=True
        ).limit(1).execute()

        if not extractions_result.data:
            return {
                'user_id': target_user_id,
                'pain_points': [],
                'top_priorities': [],
                'coverage': 0.0,
                'status': 'no_interview_data'
            }

        extraction = extractions_result.data[0]
        extraction_json = extraction.get('extraction_json', {})

        # Extract pain points with TRIPS scores
        pain_points = []
        trips_data = extraction_json.get('trips_analysis', {})
        bottlenecks = extraction_json.get('bottlenecks', [])

        # Process bottlenecks if available
        for i, bottleneck in enumerate(bottlenecks):
            if isinstance(bottleneck, dict):
                pain_point = {
                    'id': i + 1,
                    'description': bottleneck.get('description', bottleneck.get('task', '')),
                    'category': bottleneck.get('category', 'general'),
                    'trips_scores': {
                        'time': bottleneck.get('time_score', 0),
                        'repetition': bottleneck.get('repetition_score', 0),
                        'importance': bottleneck.get('importance_score', 0),
                        'pain': bottleneck.get('pain_score', 0),
                        'data': bottleneck.get('data_score', 0)
                    }
                }
                # Calculate composite score (weighted average)
                scores = pain_point['trips_scores']
                pain_point['composite_score'] = round(
                    (scores['time'] * 0.15 +
                     scores['repetition'] * 0.15 +
                     scores['importance'] * 0.30 +
                     scores['pain'] * 0.25 +
                     scores['data'] * 0.15), 2
                )
                pain_points.append(pain_point)

        # Sort by composite score and get top 3
        pain_points.sort(key=lambda x: x['composite_score'], reverse=True)
        top_priorities = pain_points[:3]

        # Calculate coverage (how many conversations address top priorities)
        # This would require matching conversation topics to pain points
        # For now, return a placeholder
        coverage = 0.0

        return {
            'user_id': target_user_id,
            'pain_points': pain_points,
            'top_priorities': top_priorities,
            'coverage': coverage,
            'completeness_score': extraction.get('completeness_score', 0),
            'status': 'active' if pain_points else 'no_pain_points'
        }

    except Exception as e:
        logger.exception("Error generating TRIPS analysis", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
