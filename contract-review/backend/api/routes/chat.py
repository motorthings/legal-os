"""
Chat endpoint routes
Handles AI chat interactions with RAG (Retrieval Augmented Generation)
"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from logger_config import get_logger
from auth import get_current_user
from database import get_supabase
from document_processor import search_similar_chunks
from system_instructions_loader import get_system_instructions_for_user
from anthropic import Anthropic
import httpx
from services.useable_output_detector import process_conversation_for_useable_output
from api.models.requests import ChatRequest
from errors import ValidationError
import os
import json
import asyncio

logger = get_logger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])
limiter = Limiter(key_func=get_remote_address)
supabase = get_supabase()

# Initialize Anthropic client with timeout configuration
# 120 second timeout prevents hung requests from consuming resources
anthropic_client = Anthropic(
    api_key=os.environ.get("ANTHROPIC_API_KEY"),
    timeout=httpx.Timeout(120.0, connect=10.0)  # 120s total, 10s connect
)


@router.post("")
@limiter.limit("20/minute")
async def chat(
    request: Request,
    chat_request: ChatRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Chat endpoint with RAG (Retrieval Augmented Generation)

    Processes user messages and generates AI responses using Claude,
    optionally enhanced with context from user's documents.

    **Request Body:**
    - conversation_id: UUID of conversation to save messages
    - message: User's question/message (1-10000 chars)
    - document_ids: Optional list of document IDs to search (uses all if empty)

    **Returns:**
    - response: AI-generated response
    - context_used: Number of document chunks used for context
    - tokens_used: Token usage statistics

    **Rate Limit:** 20 requests per minute

    **Errors:**
    - 400: Invalid request (missing required fields, message too long)
    - 401: Not authenticated
    - 429: Rate limit exceeded
    - 500: Server error (AI API failure, database error)
    """
    logger.info(
        "Chat request received",
        extra={
            "user_id": current_user['id'],
            "conversation_id": chat_request.conversation_id,
            "message_length": len(chat_request.message)
        }
    )

    try:
        # Detect simple greetings or conversational messages that don't need RAG
        simple_messages = {
            'hello', 'hi', 'hey', 'greetings', 'good morning', 'good afternoon',
            'good evening', 'howdy', 'yo', 'sup', 'what\'s up', 'whats up',
            'thanks', 'thank you', 'bye', 'goodbye', 'see you', 'ok', 'okay'
        }
        message_lower = chat_request.message.lower().strip()
        is_simple_message = message_lower in simple_messages or len(chat_request.message.split()) <= 2

        # Build context from documents using RAG (conditionally)
        context_chunks = []

        # Only search if use_rag is enabled and message isn't a simple greeting
        if chat_request.use_rag and not is_simple_message:
            logger.info("Searching knowledge base for context")

            # Get user's client_id for document filtering
            client_id = current_user.get('client_id')

            # Search all documents in the user's knowledge base
            # Note: document_ids parameter exists but is not currently used for filtering
            # min_similarity=0.0 allows search_similar_chunks to use adaptive thresholds
            # based on query type (factual vs exploratory)
            search_results = search_similar_chunks(
                chat_request.message,
                client_id,
                limit=5,
                min_similarity=0.0  # Use adaptive threshold based on query type
            )
            context_chunks = search_results
            logger.info(f"Found {len(context_chunks)} relevant chunks")
        else:
            logger.info(f"Skipping RAG - use_rag={chat_request.use_rag}, is_simple_message={is_simple_message}")

        # Load per-user system instructions
        try:
            system_prompt = get_system_instructions_for_user(
                user_id=current_user['id'],
                user_data=current_user
            )
        except FileNotFoundError as e:
            logger.warning(f"Could not load system instructions: {e}")
            user_name = current_user.get('name', 'User')
            system_prompt = (
                f"You are SuperAssistant, a helpful AI assistant for {user_name}. "
                "Provide clear, accurate, and professional assistance."
            )

        user_prompt = chat_request.message

        # Only add context if we have relevant chunks (above threshold)
        if context_chunks:
            context_parts = []
            for i, chunk in enumerate(context_chunks):
                # Build source info with metadata
                source_info = f"[Source {i+1} - Relevance: {chunk['similarity']:.2f}"

                # Add document metadata if available
                metadata = chunk.get('metadata', {})
                if metadata:
                    if metadata.get('filename'):
                        source_info += f" - File: {metadata['filename']}"
                    elif metadata.get('conversation_title'):
                        source_info += f" - Conversation: {metadata['conversation_title']}"

                source_info += "]"
                context_parts.append(f"{source_info}:\n{chunk['content']}")

            context_text = "\n\n".join(context_parts)
            user_prompt = f"""You have access to the user's knowledge base. Here are the most relevant excerpts related to their question:

<knowledge_base_context>
{context_text}
</knowledge_base_context>

User's question: {chat_request.message}

Instructions:
- Use the knowledge base context above to inform your response
- Quote or reference specific information from the context when relevant
- If the context contains the answer, use it confidently
- If the context is not relevant or doesn't fully answer the question, acknowledge this and provide the best response you can
- Be specific about which parts of your answer come from the knowledge base versus general knowledge"""

        logger.info("Calling Claude API")

        # Call Claude API with prompt caching for system instructions
        # Cached tokens are 90% cheaper - significant savings for repeated chats
        message = anthropic_client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4096,
            system=[
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"}  # Cache for 5 minutes
                }
            ],
            messages=[{"role": "user", "content": user_prompt}]
        )

        response_text = message.content[0].text

        # Extract cache statistics if available
        cache_read_tokens = getattr(message.usage, 'cache_read_input_tokens', 0) or 0
        cache_creation_tokens = getattr(message.usage, 'cache_creation_input_tokens', 0) or 0

        logger.info(
            "Response generated",
            extra={
                "output_tokens": message.usage.output_tokens,
                "input_tokens": message.usage.input_tokens,
                "cache_read_tokens": cache_read_tokens,
                "cache_creation_tokens": cache_creation_tokens
            }
        )

        # Save messages to database if conversation_id provided
        if chat_request.conversation_id:
            # Batch insert both messages in a single DB call for better performance
            messages_to_insert = [
                {
                    'conversation_id': chat_request.conversation_id,
                    'role': 'user',
                    'content': chat_request.message
                },
                {
                    'conversation_id': chat_request.conversation_id,
                    'role': 'assistant',
                    'content': response_text
                }
            ]
            supabase.table('messages').insert(messages_to_insert).execute()

            logger.info("Messages saved to conversation")

            # Process for useable output detection (Bradbury Impact Loop)
            # This runs keyword analysis to detect when useable output is achieved
            try:
                process_conversation_for_useable_output(chat_request.conversation_id)
            except Exception as detection_error:
                # Log but don't fail the request if detection fails
                logger.warning(f"Useable output detection failed: {detection_error}")

        return {
            'success': True,
            'response': response_text,
            'context_used': len(context_chunks),
            'tokens': {
                'input': message.usage.input_tokens,
                'output': message.usage.output_tokens,
                'total': message.usage.input_tokens + message.usage.output_tokens,
                'cache_read': cache_read_tokens,
                'cache_creation': cache_creation_tokens
            }
        }

    except Exception as e:
        logger.exception(
            "Error processing chat request",
            exc_info=True,
            extra={"user_id": current_user['id']}
        )
        raise


@router.post("/stream")
@limiter.limit("20/minute")
async def chat_stream(
    request: Request,
    chat_request: ChatRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Streaming chat endpoint with RAG (Retrieval Augmented Generation)

    Streams AI responses in real-time using Server-Sent Events (SSE).
    Provides better UX with incremental response display.

    **Request Body:**
    - conversation_id: UUID of conversation to save messages
    - message: User's question/message (1-10000 chars)
    - document_ids: Optional list of document IDs to search (uses all if empty)

    **Response:**
    Server-Sent Events stream with:
    - `data: {"type": "token", "content": "..."}` - Text chunks
    - `data: {"type": "done", "tokens": {...}}` - Stream complete with token stats
    - `data: {"type": "error", "error": "..."}` - Error occurred

    **Rate Limit:** 20 requests per minute

    **Errors:**
    - 400: Invalid request (missing required fields, message too long)
    - 401: Not authenticated
    - 429: Rate limit exceeded
    - 500: Server error (AI API failure, database error)
    """
    logger.info(
        "Streaming chat request received",
        extra={
            "user_id": current_user['id'],
            "conversation_id": chat_request.conversation_id,
            "message_length": len(chat_request.message)
        }
    )

    async def generate_stream():
        """Generator function for SSE stream"""
        try:
            # Detect simple greetings or conversational messages that don't need RAG
            simple_messages = {
                'hello', 'hi', 'hey', 'greetings', 'good morning', 'good afternoon',
                'good evening', 'howdy', 'yo', 'sup', 'what\'s up', 'whats up',
                'thanks', 'thank you', 'bye', 'goodbye', 'see you', 'ok', 'okay'
            }
            message_lower = chat_request.message.lower().strip()
            is_simple_message = message_lower in simple_messages or len(chat_request.message.split()) <= 2

            # Build context from documents using RAG (conditionally)
            context_chunks = []

            # Only search if use_rag is enabled and message isn't a simple greeting
            if chat_request.use_rag and not is_simple_message:
                logger.info("Searching knowledge base for context")

                # Get user's client_id for document filtering
                client_id = current_user.get('client_id')

                # Search all documents in the user's knowledge base
                search_results = search_similar_chunks(
                    chat_request.message,
                    client_id,
                    limit=5,
                    min_similarity=0.0  # Use adaptive threshold based on query type
                )
                context_chunks = search_results
                logger.info(f"Found {len(context_chunks)} relevant chunks")

                # Send context info to client
                yield f"data: {json.dumps({'type': 'context', 'count': len(context_chunks)})}\n\n"
            else:
                logger.info(f"Skipping RAG - use_rag={chat_request.use_rag}, is_simple_message={is_simple_message}")

            # Load per-user system instructions
            try:
                system_prompt = get_system_instructions_for_user(
                    user_id=current_user['id'],
                    user_data=current_user
                )
            except FileNotFoundError as e:
                logger.warning(f"Could not load system instructions: {e}")
                user_name = current_user.get('name', 'User')
                system_prompt = (
                    f"You are SuperAssistant, a helpful AI assistant for {user_name}. "
                    "Provide clear, accurate, and professional assistance."
                )

            user_prompt = chat_request.message

            # Only add context if we have relevant chunks (above threshold)
            if context_chunks:
                context_parts = []
                for i, chunk in enumerate(context_chunks):
                    # Build source info with metadata
                    source_info = f"[Source {i+1} - Relevance: {chunk['similarity']:.2f}"

                    # Add document metadata if available
                    metadata = chunk.get('metadata', {})
                    if metadata:
                        if metadata.get('filename'):
                            source_info += f" - File: {metadata['filename']}"
                        elif metadata.get('conversation_title'):
                            source_info += f" - Conversation: {metadata['conversation_title']}"

                    source_info += "]"
                    context_parts.append(f"{source_info}:\n{chunk['content']}")

                context_text = "\n\n".join(context_parts)
                user_prompt = f"""You have access to the user's knowledge base. Here are the most relevant excerpts related to their question:

<knowledge_base_context>
{context_text}
</knowledge_base_context>

User's question: {chat_request.message}

Instructions:
- Use the knowledge base context above to inform your response
- Quote or reference specific information from the context when relevant
- If the context contains the answer, use it confidently
- If the context is not relevant or doesn't fully answer the question, acknowledge this and provide the best response you can
- Be specific about which parts of your answer come from the knowledge base versus general knowledge"""

            logger.info("Calling Claude API (streaming)")

            # Call Claude API with streaming and prompt caching
            # Cached tokens are 90% cheaper - significant savings for repeated chats
            full_response = ""
            input_tokens = 0
            output_tokens = 0

            with anthropic_client.messages.stream(
                model="claude-sonnet-4-5-20250929",
                max_tokens=4096,
                system=[
                    {
                        "type": "text",
                        "text": system_prompt,
                        "cache_control": {"type": "ephemeral"}  # Cache for 5 minutes
                    }
                ],
                messages=[{"role": "user", "content": user_prompt}]
            ) as stream:
                for text in stream.text_stream:
                    full_response += text
                    # Send each chunk to the client
                    yield f"data: {json.dumps({'type': 'token', 'content': text})}\n\n"

                # Get final message with token usage
                final_message = stream.get_final_message()
                input_tokens = final_message.usage.input_tokens
                output_tokens = final_message.usage.output_tokens
                cache_read_tokens = getattr(final_message.usage, 'cache_read_input_tokens', 0) or 0
                cache_creation_tokens = getattr(final_message.usage, 'cache_creation_input_tokens', 0) or 0

            logger.info(
                "Streaming response complete",
                extra={
                    "output_tokens": output_tokens,
                    "input_tokens": input_tokens,
                    "cache_read_tokens": cache_read_tokens,
                    "cache_creation_tokens": cache_creation_tokens
                }
            )

            # Save messages to database if conversation_id provided
            if chat_request.conversation_id:
                # Batch insert both messages in a single DB call
                def save_messages():
                    messages_to_insert = [
                        {
                            'conversation_id': chat_request.conversation_id,
                            'role': 'user',
                            'content': chat_request.message
                        },
                        {
                            'conversation_id': chat_request.conversation_id,
                            'role': 'assistant',
                            'content': full_response
                        }
                    ]
                    supabase.table('messages').insert(messages_to_insert).execute()

                # Run DB insert in thread pool to avoid blocking
                await asyncio.to_thread(save_messages)
                logger.info("Messages saved to conversation")

                # Process for useable output detection (Bradbury Impact Loop)
                # Run in thread pool to avoid blocking the stream
                try:
                    await asyncio.to_thread(
                        process_conversation_for_useable_output,
                        chat_request.conversation_id
                    )
                except Exception as detection_error:
                    logger.warning(f"Useable output detection failed: {detection_error}")

            # Send completion message with token stats
            completion_data = {
                'type': 'done',
                'tokens': {
                    'input': input_tokens,
                    'output': output_tokens,
                    'total': input_tokens + output_tokens,
                    'cache_read': cache_read_tokens,
                    'cache_creation': cache_creation_tokens
                },
                'context_used': len(context_chunks)
            }
            yield f"data: {json.dumps(completion_data)}\n\n"

        except Exception as e:
            logger.exception(
                "Error processing streaming chat request",
                exc_info=True,
                extra={"user_id": current_user['id']}
            )
            # Send error to client
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )
