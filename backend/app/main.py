"""
Legal AI OS — FastAPI Application

Shared backend for all 8 Legal AI functions.
"""

import asyncio
import sys
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Recover any simulation runs left mid-flight by a previous crash. Guarded so a
    # misconfigured DATABASE_URL doesn't block startup of the rest of the app.
    try:
        from app.api.routes.simulation import db, bus
        from app.services.simulation import runner
        await db.connect()
        for stale_id in await db.list_stale_runs():
            asyncio.create_task(runner.execute_run(stale_id, db, bus))
    except Exception:
        pass
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

try:
    print("[legal-os] Loading ROI routes...", file=sys.stderr, flush=True)
    from app.api.routes import roi
    app.include_router(roi.router, prefix="/api/roi", tags=["ROI Framework"])
    print("[legal-os] ROI routes loaded", file=sys.stderr, flush=True)
except Exception:
    print("[WARN] ROI routes failed to load", file=sys.stderr, flush=True)
    traceback.print_exc(file=sys.stderr)

try:
    print("[legal-os] Loading POC Pipeline routes...", file=sys.stderr, flush=True)
    from app.api.routes import poc_pipeline
    app.include_router(poc_pipeline.router, prefix="/api/poc-pipeline", tags=["POC Pipeline"])
    print("[legal-os] POC Pipeline routes loaded", file=sys.stderr, flush=True)
except Exception:
    print("[WARN] POC Pipeline routes failed to load", file=sys.stderr, flush=True)
    traceback.print_exc(file=sys.stderr)

try:
    print("[legal-os] Loading Legal Research routes...", file=sys.stderr, flush=True)
    from app.api.routes import legal_research
    app.include_router(legal_research.router, prefix="/api/legal-research", tags=["Legal Research"])
    print("[legal-os] Legal Research routes loaded", file=sys.stderr, flush=True)
except Exception:
    print("[WARN] Legal Research routes failed to load", file=sys.stderr, flush=True)
    traceback.print_exc(file=sys.stderr)

try:
    print("[legal-os] Loading Descrybe OAuth routes...", file=sys.stderr, flush=True)
    from app.api.routes import descrybe_auth
    app.include_router(descrybe_auth.router, prefix="/api/descrybe", tags=["Descrybe"])
    print("[legal-os] Descrybe OAuth routes loaded", file=sys.stderr, flush=True)
except Exception:
    print("[WARN] Descrybe OAuth routes failed to load", file=sys.stderr, flush=True)
    traceback.print_exc(file=sys.stderr)

try:
    print("[legal-os] Loading Matters routes...", file=sys.stderr, flush=True)
    from app.api.routes import matters
    app.include_router(matters.router, prefix="/api", tags=["Matters"])
    print("[legal-os] Matters routes loaded", file=sys.stderr, flush=True)
except Exception:
    print("[WARN] Matters routes failed to load", file=sys.stderr, flush=True)
    traceback.print_exc(file=sys.stderr)

try:
    print("[legal-os] Loading Simulation routes...", file=sys.stderr, flush=True)
    from app.api.routes import simulation
    app.include_router(simulation.router, prefix="/api/simulation", tags=["Simulation"])
    print("[legal-os] Simulation routes loaded", file=sys.stderr, flush=True)
except Exception:
    print("[WARN] Simulation routes failed to load", file=sys.stderr, flush=True)
    traceback.print_exc(file=sys.stderr)

print("[legal-os] Ready", file=sys.stderr, flush=True)
