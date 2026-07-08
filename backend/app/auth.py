"""
Legal AI OS — Auth Middleware

Validates Supabase JWTs on incoming requests.
Extracts user_id and client_id from the token for RLS-compatible queries.

Usage (FastAPI dependency):
    @router.get("/something")
    async def something(user: User = Depends(get_current_user)):
        ...
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from uuid import UUID
from typing import Optional

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client, Client

from app.config import settings

import jwt as pyjwt

security = HTTPBearer(auto_error=False)

# JWKS cache
_jwks_cache: dict | None = None
_jwks_expiry: float = 0


@dataclass
class User:
    """Authenticated user extracted from Supabase JWT."""
    id: UUID           # auth.users.id
    email: str | None
    role: str          # 'admin', 'partner', 'attorney', 'paralegal', 'client'
    client_id: UUID | None = None  # set if user has a profile
    jwt: str = ""


async def verify_supabase_jwt(token: str) -> dict:
    """Verify a Supabase-issued JWT and return its claims."""
    global _jwks_cache, _jwks_expiry

    import time
    import json
    from urllib.request import urlopen

    supabase_url = settings.supabase_url
    if not supabase_url:
        raise HTTPException(status_code=500, detail="SUPABASE_URL not configured")

    project_ref = supabase_url.split("//")[1].split(".")[0]

    # Decode header to get key ID and algorithm
    try:
        header = pyjwt.get_unverified_header(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token format")

    kid = header.get("kid")
    alg = header.get("alg", "RS256")
    if not kid:
        raise HTTPException(status_code=401, detail="No kid in token header")

    # Fetch JWKS if cache expired
    if _jwks_cache is None or time.time() > _jwks_expiry:
        jwks_url = f"https://{project_ref}.supabase.co/auth/v1/.well-known/jwks.json"
        try:
            with urlopen(jwks_url) as resp:
                _jwks_cache = json.loads(resp.read())
            _jwks_expiry = time.time() + 3600  # cache 1 hour
        except Exception:
            raise HTTPException(status_code=500, detail="Failed to fetch JWKS")

    # Find the matching key
    key_data = None
    for key in _jwks_cache.get("keys", []):
        if key.get("kid") == kid:
            key_data = key
            break

    if not key_data:
        raise HTTPException(status_code=401, detail="Unknown signing key")

    # Build public key — support both RSA (RS256) and EC (ES256)
    try:
        kty = key_data.get("kty", "RSA")
        key_json = json.dumps(key_data)
        if kty == "EC":
            public_key = pyjwt.algorithms.ECAlgorithm.from_jwk(key_json)
        else:
            public_key = pyjwt.algorithms.RSAAlgorithm.from_jwk(key_json)

        claims = pyjwt.decode(
            token,
            public_key,
            algorithms=["RS256", "ES256"],
            audience="authenticated",
            options={"verify_exp": True},
        )
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    return claims


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> User:
    """FastAPI dependency: validate JWT and return User.

    Attach to any route that needs authentication:
        @router.get("/protected")
        async def protected(user: User = Depends(get_current_user)):
            ...
    """
    if credentials is None:
        # Check for token in cookie (browser clients)
        token = request.cookies.get("sb-access-token") or request.cookies.get("supabase-auth-token")
        if not token:
            raise HTTPException(status_code=401, detail="Not authenticated")
    else:
        token = credentials.credentials

    claims = await verify_supabase_jwt(token)

    user_id = UUID(claims["sub"])
    email = claims.get("email")
    role = claims.get("user_metadata", {}).get("role", "attorney")

    # Resolve client_id from user_profiles
    client_id = None
    try:
        from app.database import get_supabase
        result = (
            get_supabase()
            .table("user_profiles")
            .select("client_id")
            .eq("id", str(user_id))
            .execute()
        )
        if result.data:
            client_id = UUID(result.data[0]["client_id"])
    except Exception:
        pass

    return User(
        id=user_id,
        email=email,
        role=role,
        client_id=client_id,
        jwt=token,
    )


async def get_optional_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> User | None:
    """Like get_current_user but returns None instead of 401."""
    try:
        return await get_current_user(request, credentials)
    except HTTPException:
        return None
