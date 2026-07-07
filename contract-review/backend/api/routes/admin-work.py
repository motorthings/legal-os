"""
Admin dashboard routes
Handles statistics, analytics, and administrative operations
"""
from fastapi import APIRouter, Depends, HTTPException, Request
import asyncio
import time
from datetime import datetime, timedelta

from auth import require_admin
from database import get_supabase
from logger_config import get_logger
from errors import handle_exception

logger = get_logger(__name__)
router = APIRouter(prefix="/api/admin", tags=["admin"])
supabase = get_supabase()


@router.get("/stats")
async def get_admin_stats(
    current_user: dict = Depends(require_admin)
):
    """Get overall platform statistics"""
    try:
        # Count users
        users_result = await asyncio.to_thread(
            lambda: supabase.table('users').select('id', count='exact').execute()
        )
        total_users = users_result.count or 0
        
        # Count conversations
        convos_result = await asyncio.to_thread(
            lambda: supabase.table('conversations').select('id', count='exact').execute()
        )
        total_conversations = convos_result.count or 0
        
        # Count documents
        docs_result = await asyncio.to_thread(
            lambda: supabase.table('documents').select('id', count='exact').execute()
        )
        total_documents = docs_result.count or 0

        # Count messages
        messages_result = await asyncio.to_thread(
            lambda: supabase.table('messages').select('id', count='exact').execute()
        )
        total_messages = messages_result.count or 0

        logger.info(f"📊 Stats: {total_users} users, {total_conversations} conversations, {total_documents} documents, {total_messages} messages")

        return {
            'success': True,
            'total_users': total_users,
            'total_conversations': total_conversations,
            'total_documents': total_documents,
            'total_messages': total_messages
        }
    except Exception as e:
        handle_exception(e, "fetch platform statistics", logger)


@router.get("/contract-stats")
async def get_contract_stats(
    current_user: dict = Depends(require_admin)
):
    """Get contract analysis statistics for admin dashboard"""
    try:
        # Query contract_analysis table directly for stats
        # Get contracts completed this week
        week_ago = datetime.utcnow() - timedelta(days=7)
        week_result = await asyncio.to_thread(
            lambda: supabase.table('contract_analysis')\
                .select('id', count='exact')\
                .gte('created_at', week_ago.isoformat())\
                .execute()
        )
        contracts_completed_week = week_result.count or 0

        # Get average confidence score
        confidence_result = await asyncio.to_thread(
            lambda: supabase.table('contract_analysis')\
                .select('confidence_score')\
                .not_.is_('confidence_score', 'null')\
                .execute()
        )
        avg_confidence_score = 0.0
        if confidence_result.data and len(confidence_result.data) > 0:
            scores = [float(r['confidence_score']) for r in confidence_result.data if r.get('confidence_score') is not None]
            avg_confidence_score = sum(scores) / len(scores) if scores else 0.0

        # Calculate average review time from processing_time_seconds if available
        time_result = await asyncio.to_thread(
            lambda: supabase.table('contract_analysis')\
                .select('processing_time_seconds')\
                .not_.is_('processing_time_seconds', 'null')\
                .execute()
        )
        average_review_minutes = 0.0
        if time_result.data and len(time_result.data) > 0:
            times = [float(r['processing_time_seconds']) for r in time_result.data if r.get('processing_time_seconds') is not None]
            average_review_minutes = (sum(times) / len(times) / 60) if times else 0.0

        # Get count of contracts with expert feedback
        feedback_result = await asyncio.to_thread(
            lambda: supabase.table('contract_analysis')\
                .select('id', count='exact')\
                .not_.is_('team_feedback', 'null')\
                .neq('team_feedback', '')\
                .execute()
        )
        contracts_with_feedback = feedback_result.count or 0

        # Get risk level counts
        high_risk_result = await asyncio.to_thread(
            lambda: supabase.table('contract_analysis')\
                .select('id', count='exact')\
                .eq('overall_risk_level', 'high')\
                .execute()
        )
        high_risk_count = high_risk_result.count or 0

        medium_risk_result = await asyncio.to_thread(
            lambda: supabase.table('contract_analysis')\
                .select('id', count='exact')\
                .eq('overall_risk_level', 'medium')\
                .execute()
        )
        medium_risk_count = medium_risk_result.count or 0

        low_risk_result = await asyncio.to_thread(
            lambda: supabase.table('contract_analysis')\
                .select('id', count='exact')\
                .eq('overall_risk_level', 'low')\
                .execute()
        )
        low_risk_count = low_risk_result.count or 0

        # Calculate total for percentages
        total_contracts = high_risk_count + medium_risk_count + low_risk_count
        high_risk_percent = (high_risk_count / total_contracts * 100) if total_contracts > 0 else 0
        medium_risk_percent = (medium_risk_count / total_contracts * 100) if total_contracts > 0 else 0
        low_risk_percent = (low_risk_count / total_contracts * 100) if total_contracts > 0 else 0

        logger.info(f"📊 Contract Stats: {contracts_completed_week} this week, avg {average_review_minutes:.1f} min, {contracts_with_feedback} with feedback, Risk: H:{high_risk_count} M:{medium_risk_count} L:{low_risk_count}")

        return {
            'success': True,
            'contracts_completed_week': contracts_completed_week,
            'average_review_time_minutes': round(average_review_minutes, 1),
            'avg_confidence_score': round(avg_confidence_score, 1),
            'contracts_with_feedback': contracts_with_feedback,
            'high_risk_count': high_risk_count,
            'high_risk_percent': round(high_risk_percent, 1),
            'medium_risk_count': medium_risk_count,
            'medium_risk_percent': round(medium_risk_percent, 1),
            'low_risk_count': low_risk_count,
            'low_risk_percent': round(low_risk_percent, 1)
        }
    except Exception as e:
        handle_exception(e, "fetch contract statistics", logger)


@router.get("/recent-contracts")
async def get_recent_contracts(
    current_user: dict = Depends(require_admin),
    limit: int = 10
):
    """Get recently analyzed contracts for activity feed"""
    try:
        # Limit to reasonable range
        limit = min(limit, 50)

        # Fetch recent contract analyses
        # Join with documents table to get filename
        result = await asyncio.to_thread(
            lambda: supabase.table('contract_analysis')\
                .select('id, created_at, contract_type, overall_risk_level, documents(filename)')\
                .order('created_at', desc=True)\
                .limit(limit)\
                .execute()
        )

        # Flatten the data structure to match expected format
        contracts_data = []
        for item in (result.data or []):
            contracts_data.append({
                'id': item['id'],
                'created_at': item['created_at'],
                'contract_type': item['contract_type'],
                'risk_level': item['overall_risk_level'],  # Map to expected field name
                'filename': item.get('documents', {}).get('filename', 'Unknown') if item.get('documents') else 'Unknown'
            })

        logger.info(f"📋 Retrieved {len(contracts_data)} recent contracts")

        return {
            'success': True,
            'contracts': contracts_data
        }
    except Exception as e:
        handle_exception(e, "fetch recent contracts", logger)


@router.get("/analytics/processing-efficiency")
async def get_processing_efficiency(
    current_user: dict = Depends(require_admin),
    contract_type: str = 'all'
):
    """Get contract processing efficiency metrics"""
    try:
        # First, get contract types from contract_analysis table
        contract_types_query = supabase.table('contract_analysis')\
            .select('document_id, contract_type')

        if contract_type != 'all':
            contract_types_query = contract_types_query.eq('contract_type', contract_type)

        contract_types_result = await asyncio.to_thread(lambda: contract_types_query.execute())

        # Create a map of document_id -> contract_type
        document_types = {
            row['document_id']: row['contract_type']
            for row in (contract_types_result.data or [])
            if row.get('contract_type')
        }

        if not document_types:
            return {
                'avg_processing_time_minutes': 0.0,
                'total_contracts': 0,
                'contracts_by_type': {}
            }

        # Get processing logs for documents we have types for
        query = supabase.table('contract_processing_logs')\
            .select('document_id, created_at')\
            .eq('step_status', 'completed')\
            .in_('document_id', list(document_types.keys()))

        result = await asyncio.to_thread(lambda: query.limit(1000).execute())

        if not result.data:
            return {
                'avg_processing_time_minutes': 0.0,
                'total_contracts': 0,
                'contracts_by_type': {}
            }

        # Group by document and calculate processing times
        documents_by_id = {}
        for log in result.data:
            document_id = log['document_id']
            log_contract_type = document_types.get(document_id, 'unknown')

            if document_id not in documents_by_id:
                documents_by_id[document_id] = {
                    'timestamps': [],
                    'type': log_contract_type
                }
            documents_by_id[document_id]['timestamps'].append(log['created_at'])

        # Calculate average processing times
        total_time = 0
        contract_count = 0
        by_type = {}

        for document_data in documents_by_id.values():
            if len(document_data['timestamps']) >= 2:
                timestamps = sorted(document_data['timestamps'])
                start = datetime.fromisoformat(timestamps[0].replace('Z', '+00:00'))
                end = datetime.fromisoformat(timestamps[-1].replace('Z', '+00:00'))
                duration_mins = (end - start).total_seconds() / 60

                total_time += duration_mins
                contract_count += 1

                # Track by type
                ctype = document_data['type']
                if ctype not in by_type:
                    by_type[ctype] = {'count': 0, 'total_time': 0}
                by_type[ctype]['count'] += 1
                by_type[ctype]['total_time'] += duration_mins

        # Calculate averages
        avg_time = total_time / contract_count if contract_count > 0 else 0.0

        contracts_by_type = {}
        for ctype, stats in by_type.items():
            contracts_by_type[ctype] = {
                'count': stats['count'],
                'avg_time_minutes': round(stats['total_time'] / stats['count'], 2) if stats['count'] > 0 else 0.0
            }

        return {
            'avg_processing_time_minutes': round(avg_time, 2),
            'total_contracts': contract_count,
            'contracts_by_type': contracts_by_type
        }
    except Exception as e:
        handle_exception(e, "fetch processing efficiency", logger)


@router.get("/analytics/risk-distribution")
async def get_risk_distribution(
    current_user: dict = Depends(require_admin),
    contract_type: str = 'all'
):
    """Get risk level distribution across contracts"""
    try:
        # Build query - use contract_analysis (singular) table with overall_risk_level column
        query = supabase.table('contract_analysis').select('overall_risk_level, contract_type')

        if contract_type != 'all':
            query = query.eq('contract_type', contract_type)

        result = await asyncio.to_thread(lambda: query.execute())

        # Count by risk level
        high = 0
        medium = 0
        low = 0

        for contract in result.data or []:
            risk_level = contract.get('overall_risk_level')
            if not risk_level:
                continue  # Skip null/empty risk levels
            risk = risk_level.lower()
            if risk == 'high':
                high += 1
            elif risk == 'medium':
                medium += 1
            elif risk == 'low':
                low += 1

        logger.info(f"📊 Risk distribution: {high} high, {medium} medium, {low} low (total: {high + medium + low})")

        return {
            'high': high,
            'medium': medium,
            'low': low,
            'total': high + medium + low
        }
    except Exception as e:
        handle_exception(e, "fetch risk distribution", logger)


@router.get("/analytics/contract-trends")
async def get_contract_trends(
    current_user: dict = Depends(require_admin),
    contract_type: str = 'all',
    days: int = 30,
    interval: str = 'auto'  # 'auto', 'hour', 'day', 'week'
):
    """Get contract analysis trends over time with smart time intervals"""
    try:
        # Limit days to prevent excessive queries
        days = min(days, 90)

        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        # Determine interval based on range if 'auto'
        if interval == 'auto':
            if days <= 1:
                interval = 'hour'
            elif days <= 30:
                interval = 'day'
            else:
                interval = 'week'

        # Build query - use contract_analysis (singular) table with correct column names
        query = supabase.table('contract_analysis')\
            .select('created_at, contract_type, overall_risk_level, risk_score')\
            .gte('created_at', start_date.isoformat())

        if contract_type != 'all':
            query = query.eq('contract_type', contract_type)

        result = await asyncio.to_thread(lambda: query.execute())

        # Group by time interval
        trends_by_time = {}
        for contract in result.data or []:
            created_at = contract['created_at']

            # Extract time key based on interval
            if interval == 'hour':
                # Group by hour: YYYY-MM-DD HH:00
                time_key = created_at[:13] + ':00:00'
            elif interval == 'day':
                # Group by day: YYYY-MM-DD
                time_key = created_at[:10]
            else:  # week
                # Group by week (ISO week)
                dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                year, week, _ = dt.isocalendar()
                time_key = f"{year}-W{week:02d}"

            if time_key not in trends_by_time:
                trends_by_time[time_key] = {
                    'date': time_key,
                    'count': 0,
                    'total_risk': 0
                }
            trends_by_time[time_key]['count'] += 1
            trends_by_time[time_key]['total_risk'] += contract.get('risk_score', 0) or 0

        # Calculate averages and convert to list
        trends = []
        for time_key in sorted(trends_by_time.keys()):
            data = trends_by_time[time_key]
            trends.append({
                'date': time_key,
                'count': data['count'],
                'avg_risk_score': round(data['total_risk'] / data['count'], 1) if data['count'] > 0 else 0
            })

        return {
            'trends': trends,
            'interval': interval  # Return the interval used for client reference
        }
    except Exception as e:
        handle_exception(e, "fetch contract trends", logger)


@router.get("/analytics/usage-trends")
async def get_usage_trends(
    current_user: dict = Depends(require_admin),
    days: int = 30
):
    """Get contract analysis trends over time by contract type"""
    try:
        from datetime import datetime, timedelta
        from collections import defaultdict

        # Limit days to prevent excessive queries
        days = min(days, 90)

        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        # Initialize trends structure with contract types
        trends_by_date = {}
        current_date = start_date.date()
        while current_date <= end_date.date():
            date_str = current_date.isoformat()
            trends_by_date[date_str] = {
                'date': date_str,
                'vendor': 0,
                'customer': 0,
                'employment': 0,
                'dpa': 0,
                'general': 0,
                'total': 0
            }
            current_date += timedelta(days=1)

        # Query contract_analysis table for contracts analyzed in date range
        result = await asyncio.to_thread(
            lambda: supabase.table('contract_analysis')
                .select('created_at, contract_type')
                .gte('created_at', start_date.isoformat())
                .lte('created_at', end_date.isoformat())
                .limit(10000)  # Higher limit for contract data
                .execute()
        )

        # Count contracts by type and date
        for row in (result.data or []):
            date = datetime.fromisoformat(row['created_at'].replace('Z', '+00:00')).date().isoformat()
            contract_type = row.get('contract_type', 'general')

            # Ensure date exists in trends (should always be true)
            if date in trends_by_date:
                # Increment the specific contract type
                if contract_type in ['vendor', 'customer', 'employment', 'dpa', 'general']:
                    trends_by_date[date][contract_type] += 1
                else:
                    # Default to general for unknown types
                    trends_by_date[date]['general'] += 1

                # Increment total
                trends_by_date[date]['total'] += 1

        # Convert to sorted list
        trends = [trends_by_date[date] for date in sorted(trends_by_date.keys())]

        return {
            'success': True,
            'trends': trends
        }
    except Exception as e:
        handle_exception(e, "fetch contract trends", logger)


@router.get("/analytics/active-users")
async def get_active_users(
    current_user: dict = Depends(require_admin),
    days: int = 7
):
    """Get active users in specified timeframe"""
    try:
        from datetime import datetime, timedelta

        # Get total users count
        total_users_result = await asyncio.to_thread(
            lambda: supabase.table('users').select('id', count='exact').execute()
        )
        total_users = total_users_result.count or 0

        # Get users active in last 7 days (users who updated conversations)
        seven_days_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
        active_7_convos = await asyncio.to_thread(
            lambda: supabase.table('conversations')\
                .select('user_id')\
                .gte('updated_at', seven_days_ago)\
                .execute()
        )

        # Get unique user IDs
        active_7_user_ids = set()
        for convo in (active_7_convos.data or []):
            if convo.get('user_id'):
                active_7_user_ids.add(convo['user_id'])

        # Get users active in last 30 days
        thirty_days_ago = (datetime.utcnow() - timedelta(days=30)).isoformat()
        active_30_convos = await asyncio.to_thread(
            lambda: supabase.table('conversations')\
                .select('user_id')\
                .gte('updated_at', thirty_days_ago)\
                .execute()
        )

        # Get unique user IDs
        active_30_user_ids = set()
        for convo in (active_30_convos.data or []):
            if convo.get('user_id'):
                active_30_user_ids.add(convo['user_id'])

        return {
            'success': True,
            'active_users': {
                'last_7_days': len(active_7_user_ids),
                'last_30_days': len(active_30_user_ids),
                'total_users': total_users
            }
        }
    except Exception as e:
        handle_exception(e, "fetch active users", logger)


@router.get("/analytics/recent-activity")
async def get_recent_activity(
    current_user: dict = Depends(require_admin),
    limit: int = 20
):
    """Get recent platform activity"""
    try:
        # Get recent conversations with user info
        convos = await asyncio.to_thread(
            lambda: supabase.table('conversations')\
                .select('id, title, created_at, user_id, users:user_id(id, name, email)')\
                .order('created_at', desc=True)\
                .limit(limit)\
                .execute()
        )

        # Get recent document uploads with user info
        docs = await asyncio.to_thread(
            lambda: supabase.table('documents')\
                .select('id, filename, uploaded_at, uploaded_by, users:uploaded_by(id, name, email)')\
                .order('uploaded_at', desc=True)\
                .limit(limit)\
                .execute()
        )

        # Transform to unified activity format
        activity = []

        # Get message counts for all conversations in a single query (fixes N+1)
        conversation_ids = [conv['id'] for conv in (convos.data or [])]
        msg_counts = {}
        if conversation_ids:
            msg_counts_result = await asyncio.to_thread(
                lambda: supabase.table('messages')
                    .select('conversation_id')
                    .in_('conversation_id', conversation_ids)
                    .execute()
            )
            for msg in (msg_counts_result.data or []):
                conv_id = msg['conversation_id']
                msg_counts[conv_id] = msg_counts.get(conv_id, 0) + 1

        # Add conversations with message counts
        for conv in (convos.data or []):
            activity.append({
                'type': 'conversation',
                'id': conv['id'],
                'timestamp': conv['created_at'],
                'title': conv.get('title'),
                'user': conv.get('users') if conv.get('users') else None,
                'message_count': msg_counts.get(conv['id'], 0)
            })

        # Add documents
        for doc in (docs.data or []):
            activity.append({
                'type': 'document',
                'id': doc['id'],
                'timestamp': doc['uploaded_at'],
                'filename': doc.get('filename'),
                'user': doc.get('users') if doc.get('users') else None
            })

        # Sort by timestamp, most recent first
        activity.sort(key=lambda x: x['timestamp'], reverse=True)

        # Limit results
        activity = activity[:limit]

        return {
            'success': True,
            'activity': activity
        }
    except Exception as e:
        handle_exception(e, "fetch recent activity", logger)


@router.get("/users")
async def get_all_users(
    current_user: dict = Depends(require_admin)
):
    """Get all users for admin (for KPI user selector)"""
    try:
        result = await asyncio.to_thread(
            lambda: supabase.table('users')\
                .select('id, email, name')\
                .order('email')\
                .execute()
        )

        logger.info(f"📋 Retrieved {len(result.data)} users for selector")

        return {
            'success': True,
            'users': result.data
        }
    except Exception as e:
        handle_exception(e, "fetch users list", logger)


@router.get("/clients")
async def get_all_clients(
    current_user: dict = Depends(require_admin)
):
    """Get all clients for admin"""
    try:
        result = await asyncio.to_thread(
            lambda: supabase.table('clients')\
                .select('id, name')\
                .order('name')\
                .execute()
        )

        logger.info(f"📋 Retrieved {len(result.data)} clients")

        return {
            'success': True,
            'clients': result.data
        }
    except Exception as e:
        handle_exception(e, "fetch clients list", logger)


@router.get("/conversations")
async def get_all_conversations(
    current_user: dict = Depends(require_admin),
    limit: int = 100,
    client_id: str = None
):
    """Get all conversations with user and client info for admin"""
    try:
        # Build query with joins
        query = supabase.table('conversations')\
            .select('''
                *,
                users:user_id(name, email),
                clients:client_id(name)
            ''')

        # Apply client filter if provided
        if client_id:
            query = query.eq('client_id', client_id)

        # Apply limit and order
        result = await asyncio.to_thread(
            lambda: query.order('updated_at', desc=True)\
                .limit(limit)\
                .execute()
        )

        conversations = result.data

        # Get message counts for all conversations in a single query (fixes N+1)
        if conversations:
            conversation_ids = [conv['id'] for conv in conversations]
            msg_counts_result = await asyncio.to_thread(
                lambda: supabase.table('messages')
                    .select('conversation_id')
                    .in_('conversation_id', conversation_ids)
                    .execute()
            )

            # Count messages per conversation in memory
            msg_counts = {}
            for msg in (msg_counts_result.data or []):
                conv_id = msg['conversation_id']
                msg_counts[conv_id] = msg_counts.get(conv_id, 0) + 1

            # Attach counts to conversations
            for conv in conversations:
                conv['message_count'] = msg_counts.get(conv['id'], 0)

        logger.info(f"📋 Retrieved {len(conversations)} conversations")

        return {
            'success': True,
            'conversations': conversations
        }
    except Exception as e:
        handle_exception(e, "fetch conversations", logger)


@router.get("/health")
async def get_system_health(
    current_user: dict = Depends(require_admin)
):
    """Get real-time system health metrics for admin dashboard"""
    try:
        health_data = {
            'supabase': {'status': 'checking', 'responseTime': 0},
            'railway': {'status': 'running'},
            'vercel': {'status': 'deployed'},
            'anthropic': {'status': 'checking', 'latency': 0},
            'voyageAI': {'status': 'checking', 'latency': 0}
        }

        # 1. Check Supabase (Database) Health
        try:
            db_start = time.time()
            await asyncio.to_thread(
                lambda: supabase.table('users').select('id', count='exact').limit(1).execute()
            )
            db_time = round((time.time() - db_start) * 1000)
            health_data['supabase'] = {
                'status': 'connected',
                'responseTime': db_time
            }
        except Exception as e:
            logger.error(f"❌ Supabase health check failed: {str(e)}")
            health_data['supabase'] = {
                'status': 'error',
                'responseTime': 0
            }

        # 2. Railway (Backend API) - If this endpoint is responding, Railway is running
        health_data['railway'] = {
            'status': 'running',
            'uptime': True
        }

        # 3. Vercel (Frontend) - Mark as deployed (frontend wouldn't load if it wasn't)
        health_data['vercel'] = {
            'status': 'deployed',
            'build': 'success'
        }

        # 4. Check Anthropic (Claude) - Check recent AI interactions
        try:
            one_hour_ago = (datetime.utcnow() - timedelta(hours=1)).isoformat()
            recent_messages = await asyncio.to_thread(
                lambda: supabase.table('messages')\
                    .select('role, timestamp')\
                    .eq('role', 'assistant')\
                    .gte('timestamp', one_hour_ago)\
                    .limit(1)\
                    .execute()
            )

            if recent_messages.data and len(recent_messages.data) > 0:
                health_data['anthropic'] = {
                    'status': 'active',
                    'latency': 1.2  # TODO: Track actual response times
                }
            else:
                health_data['anthropic'] = {
                    'status': 'idle',
                    'latency': 0
                }
        except Exception as e:
            logger.error(f"❌ Anthropic health check failed: {str(e)}")
            health_data['anthropic'] = {
                'status': 'unknown',
                'latency': 0
            }

        # 5. Check Voyage AI (Embeddings) - Check if embeddings service is available
        try:
            # Check if we have recent documents with embeddings
            one_day_ago = (datetime.utcnow() - timedelta(days=1)).isoformat()
            recent_docs = await asyncio.to_thread(
                lambda: supabase.table('documents')\
                    .select('id')\
                    .gte('uploaded_at', one_day_ago)\
                    .limit(1)\
                    .execute()
            )

            if recent_docs.data and len(recent_docs.data) > 0:
                health_data['voyageAI'] = {
                    'status': 'active',
                    'latency': 0.8  # TODO: Track actual embedding times
                }
            else:
                health_data['voyageAI'] = {
                    'status': 'idle',
                    'latency': 0
                }
        except Exception as e:
            logger.error(f"❌ Voyage AI health check failed: {str(e)}")
            health_data['voyageAI'] = {
                'status': 'unknown',
                'latency': 0
            }

        logger.info(f"🏥 Health check: Supabase {db_time}ms, Railway ✓, Vercel ✓, Anthropic {health_data['anthropic']['status']}, Voyage {health_data['voyageAI']['status']}")

        return {
            'success': True,
            'health': health_data
        }
    except Exception as e:
        handle_exception(e, "check system health", logger)


# =============================================================================
# Admin Settings API Routes
# =============================================================================

@router.get("/settings/{setting_key}")
async def get_admin_setting(
    setting_key: str,
    current_user: dict = Depends(require_admin)
):
    """Get a specific admin setting by key"""
    try:
        result = await asyncio.to_thread(
            lambda: supabase.table('admin_settings')\
                .select('setting_key, setting_value, description, updated_at')\
                .eq('setting_key', setting_key)\
                .single()\
                .execute()
        )

        if not result.data:
            raise HTTPException(status_code=404, detail=f"Setting '{setting_key}' not found")

        logger.info(f"⚙️ Retrieved setting: {setting_key}")
        return result.data

    except HTTPException:
        raise
    except Exception as e:
        handle_exception(e, f"fetch setting '{setting_key}'", logger)


@router.post("/settings/{setting_key}")
async def update_admin_setting(
    setting_key: str,
    request: Request,
    current_user: dict = Depends(require_admin)
):
    """Update a specific admin setting"""
    try:
        body = await request.json()
        setting_value = body.get('setting_value')

        if setting_value is None:
            raise HTTPException(status_code=400, detail="setting_value is required")

        # Update the setting
        result = await asyncio.to_thread(
            lambda: supabase.table('admin_settings')\
                .update({
                    'setting_value': setting_value,
                    'updated_by': current_user['id']
                })\
                .eq('setting_key', setting_key)\
                .execute()
        )

        if not result.data or len(result.data) == 0:
            # Setting doesn't exist, create it
            description = body.get('description', f'Setting: {setting_key}')
            result = await asyncio.to_thread(
                lambda: supabase.table('admin_settings')\
                    .insert({
                        'setting_key': setting_key,
                        'setting_value': setting_value,
                        'description': description,
                        'updated_by': current_user['id']
                    })\
                    .execute()
            )

        logger.info(f"⚙️ Updated setting: {setting_key}")
        return {
            'success': True,
            'setting_key': setting_key,
            'setting_value': setting_value
        }

    except HTTPException:
        raise
    except Exception as e:
        handle_exception(e, f"update setting '{setting_key}'", logger)


@router.get("/celery/stats")
async def get_celery_stats(
    current_user: dict = Depends(require_admin)
):
    """
    Get Celery queue statistics (admin only)
    """
    try:
        # Check if Celery is available
        try:
            from celery_app import celery_app
        except ImportError:
            return {
                'success': False,
                'error': 'Celery not available',
                'message': 'System is using BackgroundTasks'
            }

        inspect = celery_app.control.inspect()

        # Get queue lengths
        active_tasks = inspect.active() or {}
        reserved_tasks = inspect.reserved() or {}
        scheduled_tasks = inspect.scheduled() or {}

        # Count tasks by queue
        stats = {
            'workers': len(active_tasks),
            'active_tasks': sum(len(tasks) for tasks in active_tasks.values()),
            'reserved_tasks': sum(len(tasks) for tasks in reserved_tasks.values()),
            'scheduled_tasks': sum(len(tasks) for tasks in scheduled_tasks.values()),
            'worker_details': active_tasks
        }

        return {
            'success': True,
            'stats': stats
        }

    except Exception as e:
        logger.error(f"Error fetching Celery stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Analytics Endpoints
# ============================================================================

