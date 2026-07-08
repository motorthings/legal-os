"""
Legal AI OS — FastAPI Application

Shared backend for all 8 Legal AI functions.
"""

import sys
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    try:
        from app.database import close_pool
        await close_pool()
    except Exception:
        pass


app = FastAPI(
    title="Legal AI OS",
    description="Governed AI platform for legal enterprises. Eight functions. One governance layer.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost:\d+|legal\.sickofancy\.ai|legal-os\..*\.vercel\.app|legal-os\.vercel\.app)",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "app": settings.app_name,
        "env": settings.app_env,
        "llm_provider": settings.llm_provider,
    }


@app.get("/api/governance/health")
async def governance_health():
    try:
        from app.database import get_supabase
        result = get_supabase().table("functions").select("*").execute()
        functions = [
            {"slug": f["slug"], "name": f["name"], "status": f["status"], "version": f["version"]}
            for f in (result.data or [])
        ]
    except Exception:
        traceback.print_exc()
        functions = []

    return {
        "platform": "Legal AI OS",
        "functions": functions,
        "governance_pillars": ["auditability", "explainability", "traceability"],
        "llm_provider": settings.llm_provider,
    }


print("[legal-os] Starting up...", file=sys.stderr, flush=True)

# Mount routers — isolated so one bad import doesn't kill the app
try:
    print("[legal-os] Loading due_diligence routes...", file=sys.stderr, flush=True)
    from app.api.routes import due_diligence
    app.include_router(due_diligence.router, prefix="/api/due-diligence", tags=["Due Diligence"])
    print("[legal-os] due_diligence routes loaded", file=sys.stderr, flush=True)
except Exception:
    print("[WARN] due_diligence routes failed to load", file=sys.stderr, flush=True)
    traceback.print_exc(file=sys.stderr)

try:
    print("[legal-os] Loading reporting routes...", file=sys.stderr, flush=True)
    from app.api.routes import reporting
    app.include_router(reporting.router, prefix="/api/reporting", tags=["Client Value Reporting"])
    print("[legal-os] reporting routes loaded", file=sys.stderr, flush=True)
except Exception:
    print("[WARN] reporting routes failed to load", file=sys.stderr, flush=True)
    traceback.print_exc(file=sys.stderr)

try:
    print("[legal-os] Loading regulatory routes...", file=sys.stderr, flush=True)
    from app.api.routes import regulatory
    app.include_router(regulatory.router, prefix="/api/regulatory", tags=["Regulatory Change Monitor"])
    print("[legal-os] regulatory routes loaded", file=sys.stderr, flush=True)
except Exception:
    print("[WARN] regulatory routes failed to load", file=sys.stderr, flush=True)
    traceback.print_exc(file=sys.stderr)

try:
    print("[legal-os] Loading KM routes...", file=sys.stderr, flush=True)
    from app.api.routes import km
    app.include_router(km.router, prefix="/api/km", tags=["KM & Precedent Intelligence"])
    print("[legal-os] KM routes loaded", file=sys.stderr, flush=True)
except Exception:
    print("[WARN] KM routes failed to load", file=sys.stderr, flush=True)
    traceback.print_exc(file=sys.stderr)

print("[legal-os] Ready", file=sys.stderr, flush=True)
