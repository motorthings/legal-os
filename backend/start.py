#!/usr/bin/env python3
"""Startup wrapper that catches and logs all errors before uvicorn starts."""
import sys
import traceback

print("[legal-os] Starting startup wrapper...", flush=True)

try:
    import uvicorn
    print("[legal-os] uvicorn imported OK", flush=True)

    print("[legal-os] Starting uvicorn...", flush=True)
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8080,
        log_level="info",
    )
except Exception as e:
    print(f"[legal-os] FATAL: {e}", flush=True)
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)
