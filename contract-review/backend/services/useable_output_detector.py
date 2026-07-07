"""
Useable Output Detection Service
Blended approach using multiple signals to detect when AI output becomes useable
"""
from typing import Optional, Tuple
from datetime import datetime
from database import get_supabase
from logger_config import get_logger

logger = get_logger(__name__)
supabase = get_supabase()

# Positive confirmation keywords indicating useable output
CONFIRMATION_KEYWORDS = [
    # Acceptance
    'perfect', 'exactly', 'great', 'excellent', 'awesome',
    # Gratitude
    'thanks', 'thank you', 'appreciate', 'appreciated',
    # Agreement
    'that works', 'this works', 'works for me', 'sounds good',
    # Completion
    'got it', 'understood', 'makes sense', 'i can work with this',
    'this is what i needed', 'just what i needed',
    # Positive affirmation
    'yes this is good', 'yes perfect', 'thats it', "that's it",
    'spot on', 'bang on', 'nailed it'
]

# Strong negative indicators (user is still iterating)
ITERATION_KEYWORDS = [
    'actually', 'but', 'however', 'instead', 'no not',
    'can you change', 'modify', 'adjust', 'fix this',
    'thats not quite', "that's not quite", 'not exactly'
]


def detect_confirmation_keywords(message_content: str) -> bool:
    """
    Detect if user message contains positive confirmation keywords

    Args:
        message_content: The user's message content

    Returns:
        True if confirmation detected, False otherwise
    """
    content_lower = message_content.lower().strip()

    # Check for negative indicators first (higher priority)
    if any(keyword in content_lower for keyword in ITERATION_KEYWORDS):
        return False

    # Check for positive confirmation
    return any(keyword in content_lower for keyword in CONFIRMATION_KEYWORDS)


def calculate_turns_to_message(conversation_id: str, message_id: str) -> int:
    """
    Calculate number of user turns up to and including a specific message

    Args:
        conversation_id: The conversation ID
        message_id: The message ID to count up to

    Returns:
        Number of user turns
    """
    try:
        # Get the target message timestamp
        target_msg = supabase.table('messages').select(
            'timestamp'
        ).eq('id', message_id).execute()

        if not target_msg.data:
            return 0

        target_timestamp = target_msg.data[0]['timestamp']

        # Count user messages up to this timestamp
        user_messages = supabase.table('messages').select(
            'id'
        ).eq('conversation_id', conversation_id).eq(
            'role', 'user'
        ).lte(
            'timestamp', target_timestamp
        ).execute()

        return len(user_messages.data) if user_messages.data else 0

    except Exception as e:
        logger.error(f"Error calculating turns to message: {e}")
        return 0


def mark_useable_output(
    conversation_id: str,
    message_id: str,
    method: str,
    user_id: Optional[str] = None
) -> bool:
    """
    Mark a message as useable output in the database

    Args:
        conversation_id: The conversation ID
        message_id: The assistant message ID that provided useable output
        method: Detection method (user_marked, copy_event, keyword_detected, etc.)
        user_id: Optional user ID for verification

    Returns:
        True if successfully marked, False otherwise
    """
    try:
        # Check if already marked (don't override)
        existing = supabase.table('conversations').select(
            'useable_output_message_id'
        ).eq('id', conversation_id).execute()

        if existing.data and existing.data[0].get('useable_output_message_id'):
            logger.info(f"Conversation {conversation_id} already has useable output marked")
            return True  # Already marked, that's fine

        # Calculate turns to this message
        turns = calculate_turns_to_message(conversation_id, message_id)

        # Update conversation
        result = supabase.table('conversations').update({
            'useable_output_message_id': message_id,
            'turns_to_useable_output': turns,
            'useable_output_method': method,
            'useable_output_detected_at': datetime.utcnow().isoformat()
        }).eq('id', conversation_id).execute()

        logger.info(
            f"Marked useable output for conversation {conversation_id}: "
            f"message={message_id}, turns={turns}, method={method}"
        )

        return True

    except Exception as e:
        logger.error(f"Error marking useable output: {e}")
        return False


def auto_detect_useable_output(conversation_id: str) -> Optional[Tuple[str, str, int]]:
    """
    Automatically detect useable output using multiple signals

    Checks in priority order:
    1. Copy events (tracked separately)
    2. Keyword analysis in user responses
    3. Function completion (future)
    4. Conversation end pattern (fallback)

    Args:
        conversation_id: The conversation ID to analyze

    Returns:
        Tuple of (message_id, method, turns) if detected, None otherwise
    """
    try:
        # Get all messages in conversation
        messages = supabase.table('messages').select(
            'id, role, content, timestamp'
        ).eq('conversation_id', conversation_id).order(
            'timestamp', desc=False
        ).execute()

        if not messages.data or len(messages.data) < 2:
            return None

        # Analyze conversation flow
        for i, msg in enumerate(messages.data):
            # Skip if not a user message
            if msg['role'] != 'user':
                continue

            # Check for confirmation keywords in user message
            if detect_confirmation_keywords(msg['content']):
                # Previous message (assistant) was the useable output
                if i > 0 and messages.data[i-1]['role'] == 'assistant':
                    assistant_msg_id = messages.data[i-1]['id']
                    turns = calculate_turns_to_message(conversation_id, assistant_msg_id)
                    logger.info(
                        f"Auto-detected useable output via keywords in conversation {conversation_id}"
                    )
                    return (assistant_msg_id, 'keyword_detected', turns)

        # Fallback: If conversation has ended naturally (no activity recently)
        # Use the last assistant message
        last_messages = [m for m in messages.data if m['role'] == 'assistant']
        if last_messages:
            last_assistant_msg = last_messages[-1]
            turns = calculate_turns_to_message(conversation_id, last_assistant_msg['id'])
            return (last_assistant_msg['id'], 'conversation_ended', turns)

        return None

    except Exception as e:
        logger.error(f"Error auto-detecting useable output: {e}")
        return None


def process_conversation_for_useable_output(conversation_id: str) -> bool:
    """
    Process a conversation to detect and mark useable output if not already marked

    Args:
        conversation_id: The conversation ID

    Returns:
        True if useable output detected/marked, False otherwise
    """
    try:
        # Check if already marked
        existing = supabase.table('conversations').select(
            'useable_output_message_id'
        ).eq('id', conversation_id).execute()

        if existing.data and existing.data[0].get('useable_output_message_id'):
            return True  # Already marked

        # Auto-detect
        detection = auto_detect_useable_output(conversation_id)

        if detection:
            message_id, method, turns = detection
            return mark_useable_output(conversation_id, message_id, method)

        return False

    except Exception as e:
        logger.error(f"Error processing conversation for useable output: {e}")
        return False
