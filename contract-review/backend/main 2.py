"""
SuperAssistant MVP - Main Application Entry Point

This is a clean, modular FastAPI application with route separation.
All endpoint logic has been moved to dedicated route modules for maintainability.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import os
from concurrent.futures import ThreadPoolExecutor
import asyncio
from dotenv import load_dotenv

# Load environment variables BEFORE any other imports
load_dotenv()

from database import get_supabase
from errors import APIError, api_error_handler, generic_error_handler
from api.utils.error_handler import (
    SuperAssistantError,
    superassistant_error_handler,
    http_exception_handler
)
from logger_config import setup_logging, get_logger

# Initialize logging
setup_logging()
logger = get_logger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Initialize FastAPI app
app = FastAPI(
    title="SuperAssistant API",
    description="Backend API for SuperAssistant MVP - AI-powered executive assistant",
    version="1.0.0"
)

# Configure app state
app.state.limiter = limiter

# Register exception handlers (order matters - more specific first)
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_exception_handler(SuperAssistantError, superassistant_error_handler)
app.add_exception_handler(APIError, api_error_handler)
app.add_exception_handler(Exception, generic_error_handler)

# ============================================================================
# CORS Middleware Configuration
# ============================================================================

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")
allowed_origins = [origin.strip() for origin in FRONTEND_URL.split(",")]

# Always include production Vercel frontend
if "https://superassistant-mvp.vercel.app" not in allowed_origins:
    allowed_origins.append("https://superassistant-mvp.vercel.app")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],  # Explicit headers instead of wildcard
)

# Add GZip compression for responses > 1000 bytes (30-50% size reduction)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Configure thread pool for asyncio.to_thread() calls
# This prevents thread exhaustion under high load
_thread_pool = ThreadPoolExecutor(max_workers=20)
asyncio.get_event_loop().set_default_executor(_thread_pool)

# Initialize Supabase connection
supabase = get_supabase()

# ============================================================================
# Import and Register Route Modules
# ============================================================================

# Import all route modules
from api.routes import chat, kpis
from api.routes import conversations, documents, users
from api.routes import google_drive, notion, interviews
from api.routes import admin, system_instructions, document_mappings, clients
from api.routes import quick_prompts
from api.routes import theme

# Register routers
app.include_router(chat.router)
app.include_router(kpis.router)
app.include_router(conversations.router)
app.include_router(documents.router)
app.include_router(users.router)
app.include_router(google_drive.router)
app.include_router(notion.router)
app.include_router(interviews.router)
app.include_router(admin.router)
app.include_router(system_instructions.router)
app.include_router(document_mappings.router)
app.include_router(clients.router)
app.include_router(quick_prompts.router)
app.include_router(theme.router)

logger.info("✅ All route modules registered")

# ============================================================================
# Backward Compatibility Routes
# ============================================================================

from fastapi import Depends, HTTPException
from auth import get_current_user
from validation import validate_uuid
import asyncio

@app.get("/api/clients/{client_id}/conversations")
async def list_client_conversations(
    client_id: str,
    include_archived: bool = False,
    current_user: dict = Depends(get_current_user),
    limit: int = 50,
    offset: int = 0
):
    """List all conversations for a client (backward compatibility)"""
    try:
        validate_uuid(client_id, "client_id")

        # Enforce reasonable limits
        limit = min(limit, 100)

        query = supabase.table('conversations')\
            .select('id, title, user_id, client_id, created_at, updated_at, archived, in_knowledge_base', count='exact')\
            .eq('client_id', client_id)

        if not include_archived:
            query = query.eq('archived', False)

        result = await asyncio.to_thread(
            lambda: query.order('updated_at', desc=True).limit(limit).offset(offset).execute()
        )

        return {
            'success': True,
            'conversations': result.data,
            'total': result.count,
            'limit': limit,
            'offset': offset
        }

    except Exception as e:
        logger.error(f"❌ Error listing client conversations: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/users/me/storage")
async def get_user_storage(
    current_user: dict = Depends(get_current_user)
):
    """Get user storage info (backward compatibility - forwards to documents router)"""
    try:
        # Query user storage from database
        result = await asyncio.to_thread(
            lambda: supabase.table('users')\
                .select('storage_used, storage_quota')\
                .eq('id', current_user['id'])\
                .single()\
                .execute()
        )

        if not result.data:
            raise HTTPException(status_code=404, detail="User not found")

        storage_quota = result.data.get('storage_quota') or 524288000  # 500MB default
        storage_used = result.data.get('storage_used') or 0

        return {
            'success': True,
            'storage_quota': storage_quota,
            'storage_used': storage_used,
            'storage_available': max(0, storage_quota - storage_used),
            'usage_percentage': round((storage_used / storage_quota * 100), 2) if storage_quota > 0 else 0
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching storage data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/users/me/documents")
async def get_user_documents(
    current_user: dict = Depends(get_current_user),
    limit: int = 50,
    offset: int = 0
):
    """Get user documents (backward compatibility - forwards to documents router)"""
    try:
        # Enforce reasonable limits
        limit = min(limit, 100)

        # Query user's documents from database with pagination
        result = await asyncio.to_thread(
            lambda: supabase.table('documents')
                .select('id, filename, storage_path, file_size, processing_status, uploaded_at, is_core_document', count='exact')
                .eq('uploaded_by', current_user['id'])
                .order('uploaded_at', desc=True)
                .limit(limit)
                .offset(offset)
                .execute()
        )

        return {
            'success': True,
            'documents': result.data,
            'total': result.count,
            'limit': limit,
            'offset': offset
        }

    except Exception as e:
        logger.error(f"❌ Error fetching user documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# Application Lifecycle Events
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize services on application startup"""
    try:
        from services.sync_scheduler import start_scheduler
        # Start the Google Drive sync scheduler (checks every 5 minutes)
        start_scheduler(check_interval_minutes=5)
        logger.info("✅ Application startup complete - Sync scheduler started")
    except Exception as e:
        logger.error(f"⚠️ Warning: Could not start scheduler: {e}")
        # Don't fail startup if scheduler fails


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown"""
    try:
        from services.sync_scheduler import stop_scheduler
        stop_scheduler()
        logger.info("✅ Application shutdown complete")
    except Exception as e:
        logger.error(f"⚠️ Warning during shutdown: {e}")


# ============================================================================
# Core Health Endpoints
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint - API status"""
    return {
        "message": "SuperAssistant API is running",
        "version": "1.0.0",
        "status": "healthy"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    try:
        # Test database connection
        supabase.table('users').select('id').limit(1).execute()

        return {
            "status": "healthy",
            "database": "connected",
            "version": "1.0.0"
        }
    except Exception as e:
        logger.error(f"❌ Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }


# ============================================================================
# Application Information
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True
    )
