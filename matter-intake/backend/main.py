"""Matter Intake Evaluator — FastAPI application entry point."""

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from logger import get_logger, setup_logging

load_dotenv()
setup_logging()

log = get_logger("main")

app = FastAPI(
    title="Matter Intake Evaluator",
    description="AI-powered legal matter intake evaluation for Perkins Coie",
    version="1.0.0",
)

# CORS — wide open for demo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


# Register routes (import after app creation to avoid circular imports)
from api.routes import router

app.include_router(router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=True,
    )
