"""
Contract Review Application - Main Application Entry Point

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

# Print startup info for debugging Railway deployments
print("=" * 70)
print("🚀 Starting Contract Review Backend API")
print(f"   SUPABASE_URL: {os.environ.get('SUPABASE_URL', 'NOT SET')}")
print(f"   ANTHROPIC_API_KEY: {'SET' if os.environ.get('ANTHROPIC_API_KEY') else 'NOT SET'}")
print(f"   FRONTEND_URL: {os.environ.get('FRONTEND_URL', 'NOT SET')}")
print("=" * 70)

try:
    from database import get_supabase
    print("✓ database module imported")
except Exception as e:
    print(f"✗ Failed to import database: {e}")
    raise

try:
    from errors import APIError, api_error_handler, generic_error_handler
    print("✓ errors module imported")
except Exception as e:
    print(f"✗ Failed to import errors: {e}")
    raise

try:
    from api.utils.error_handler import (
        SuperAssistantError,
        superassistant_error_handler,
        http_exception_handler
    )
    print("✓ api.utils.error_handler imported")
except Exception as e:
    print(f"✗ Failed to import error_handler: {e}")
    raise

try:
    from logger_config import setup_logging, get_logger
    print("✓ logger_config imported")
except Exception as e:
    print(f"✗ Failed to import logger_config: {e}")
    raise

# Initialize logging
setup_logging()
logger = get_logger(__name__)
print("✓ Logging initialized")

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Initialize FastAPI app
app = FastAPI(
    title="Contract Review API",
    description="Backend API for Contract Review Application - AI-powered contract analysis",
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

# Log CORS configuration for debugging (using print since logger isn't ready yet)
print("=" * 60)
print("🔧 CORS Configuration:")
print(f"   FRONTEND_URL env var: {FRONTEND_URL}")
print(f"   Allowed origins: {allowed_origins}")
print("=" * 60)

# Always include production Vercel frontends
if "https://superassistant-mvp.vercel.app" not in allowed_origins:
    allowed_origins.append("https://superassistant-mvp.vercel.app")
if "https://contract-review-liard.vercel.app" not in allowed_origins:
    allowed_origins.append("https://contract-review-liard.vercel.app")

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
# from api.routes import google_drive, notion, interviews  # Not needed for contract review
from api.routes import admin, system_instructions, document_mappings, clients
# from api.routes import quick_prompts  # Not needed for contract review
from api.routes import theme
from api.routes import contracts, legal_standards, processing_logs

# Register routers
app.include_router(chat.router)
app.include_router(kpis.router)
app.include_router(conversations.router)
app.include_router(documents.router)
app.include_router(contracts.router)  # Contract-specific routes
app.include_router(legal_standards.router)  # Legal standards management
app.include_router(processing_logs.router)  # Processing logs for transparency
app.include_router(users.router)
# app.include_router(google_drive.router)  # Not needed
# app.include_router(notion.router)  # Not needed
# app.include_router(interviews.router)  # Not needed
app.include_router(admin.router)
app.include_router(system_instructions.router)
app.include_router(document_mappings.router)
app.include_router(clients.router)
# app.include_router(quick_prompts.router)  # Not needed
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
    # Google Drive sync not needed for contract review app
    logger.info("✅ Application startup complete")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown"""
    logger.info("✅ Application shutdown complete")


# ============================================================================
# Core Health Endpoints
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint - API status"""
    return {
        "message": "Contract Review API is running",
        "version": "1.0.0",
        "status": "healthy"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    try:
        # Test database connection
        await asyncio.to_thread(
            lambda: supabase.table('users').select('id').limit(1).execute()
        )

        return {
            "status": "healthy",
            "database": "connected",
            "version": "1.0.0"
        }
    except Exception as e:
        logger.error(f"❌ Health check failed: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e)
            }
        )


@app.get("/health/celery")
async def health_check_celery():
    """
    Check Celery worker and Redis connectivity
    """
    try:
        # Check if Celery is available
        try:
            from celery_app import celery_app
            celery_available = True
        except ImportError:
            return {
                'status': 'disabled',
                'celery': 'not_installed',
                'message': 'Celery is not available (using BackgroundTasks)'
            }

        # Check Redis connection
        try:
            celery_app.broker_connection().ensure_connection(max_retries=3)
            redis_connected = True
        except Exception as e:
            return {
                'status': 'unhealthy',
                'redis': 'disconnected',
                'error': str(e)
            }

        # Check active workers
        inspect = celery_app.control.inspect()
        active_workers = inspect.active()

        worker_count = len(active_workers) if active_workers else 0

        return {
            'status': 'healthy' if worker_count > 0 else 'degraded',
            'redis': 'connected',
            'workers': worker_count,
            'queues': ['default', 'urgent', 'batch'],
            'celery_available': celery_available
        }
    except Exception as e:
        logger.error(f"❌ Celery health check failed: {str(e)}")
        return {
            'status': 'unhealthy',
            'error': str(e)
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
