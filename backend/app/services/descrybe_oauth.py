"""
Legal AI OS — Descrybe OAuth Service

Hosts the in-app "Connect Descrybe" flow. Descrybe has no static API keys;
each user authorizes the app via OAuth 2.0 Authorization Code + PKCE, and we
store the resulting refresh token (encrypted at rest) so the backend can call
the Descrybe Legal Engine MCP endpoint on their behalf.

Flow:
    connect    -> build PKCE authorize URL, stash state+verifier in a signed cookie
    callback   -> exchange code, encrypt + persist TokenSet to Supabase
    get_token  -> load + auto-refresh the user's access token
    disconnect -> drop the stored connection

Uses the ``descrybe-legal-engine`` SDK's OAuthClient primitives. No network
call happens in this module unless the token is missing or expired.
"""

from __future__ import annotations

import base64
import json
import time
from typing import Any, Optional
from uuid import UUID

from descrybe_legal_engine.auth import (
    OAuthClient,
    OAuthClientRegistration,
    OAuthMetadata,
    create_code_verifier,
)
from descrybe_legal_engine.config import DLEConfig
from descrybe_legal_engine.tokens import TokenSet

from app.config import settings
from app.database import get_supabase


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
def _dle_config() -> DLEConfig:
    """Build a DLEConfig from app settings (not from DLE_* env vars)."""
    scopes = tuple(s for s in settings.descrybe_oauth_scopes.split() if s)
    return DLEConfig(
        issuer_url=settings.descrybe_issuer_url.rstrip("/"),
        mcp_url=settings.descrybe_mcp_url,
        scopes=scopes,
        timeout_seconds=settings.descrybe_timeout_seconds,
    )


def _redirect_uri() -> str:
    """OAuth callback URL registered with Descrybe."""
    return settings.descrybe_redirect_uri or "http://localhost:8080/api/descrybe/callback"


# ---------------------------------------------------------------------------
# At-rest encryption (Fernet). Falls back to plaintext in local dev when no
# key is configured — set DESCRYBE_TOKEN_KEY in production.
# ---------------------------------------------------------------------------
def _fernet():
    if not settings.descrybe_token_key:
        return None
    try:
        from cryptography.fernet import Fernet
        return Fernet(settings.descrybe_token_key.encode())
    except Exception:
        return None


def _encrypt(value: str | None) -> str | None:
    if value is None:
        return None
    f = _fernet()
    if f is None:
        return "plain:" + value
    return "enc:" + f.encrypt(value.encode()).decode()


def _decrypt(value: str | None) -> str | None:
    if value is None:
        return None
    if value.startswith("enc:"):
        f = _fernet()
        if f is None:
            raise RuntimeError("DESCRYBE_TOKEN_KEY missing — cannot decrypt stored token")
        return f.decrypt(value[4:].encode()).decode()
    if value.startswith("plain:"):
        return value[6:]
    return value


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------
def _row_to_token_set(row: dict) -> TokenSet:
    scopes = tuple((row.get("scopes") or "").split()) if row.get("scopes") else ()
    return TokenSet(
        access_token=_decrypt(row.get("access_token")),
        token_type=row.get("token_type") or "Bearer",
        refresh_token=_decrypt(row.get("refresh_token")),
        expires_at=float(row["expires_at"]) if row.get("expires_at") is not None else None,
        scopes=scopes,
        client_id=row.get("oauth_client_id"),
        client_secret=_decrypt(row.get("oauth_client_secret")),
        token_endpoint=row.get("token_endpoint"),
    )


def _upsert_connection(user_id: UUID, token_set: TokenSet) -> None:
    row = {
        "user_id": str(user_id),
        "oauth_client_id": token_set.client_id,
        "oauth_client_secret": _encrypt(token_set.client_secret),
        "token_endpoint": token_set.token_endpoint,
        "access_token": _encrypt(token_set.access_token),
        "refresh_token": _encrypt(token_set.refresh_token),
        "token_type": token_set.token_type,
        "scopes": " ".join(token_set.scopes),
        "expires_at": token_set.expires_at,
        "status": "active",
    }
    get_supabase().table("descrybe_connections").upsert(row, on_conflict="user_id").execute()


def get_connection(user_id: UUID) -> TokenSet | None:
    """Load a stored connection (if any). Does not refresh."""
    result = (
        get_supabase()
        .table("descrybe_connections")
        .select("*")
        .eq("user_id", str(user_id))
        .eq("status", "active")
        .limit(1)
        .execute()
    )
    if not result.data:
        return None
    return _row_to_token_set(result.data[0])


def get_access_token(user_id: UUID) -> str | None:
    """Return a valid access token for a user, refreshing if needed."""
    token = get_connection(user_id)
    if token is None:
        return None
    if token.is_expired() and token.refresh_token:
        token = OAuthClient(_dle_config()).refresh(token)
        _upsert_connection(user_id, token)
    return token.access_token


def is_connected(user_id: UUID) -> bool:
    return get_connection(user_id) is not None


def disconnect(user_id: UUID) -> None:
    get_supabase().table("descrybe_connections").delete().eq("user_id", str(user_id)).execute()


# ---------------------------------------------------------------------------
# OAuth connect / callback
# ---------------------------------------------------------------------------
def _oauth_client() -> OAuthClient:
    return OAuthClient(_dle_config())


def discover_metadata() -> OAuthMetadata:
    return _oauth_client().discover_metadata()


def build_connect(user_id: UUID, return_to: str | None = None) -> dict:
    """
    Prepare the Descrybe authorization URL.

    The PKCE verifier and client metadata are embedded (Fernet-encrypted) in
    the OAuth ``state`` parameter itself, so they survive the browser
    round-trip without a cookie — cross-origin fetches won't store cookies.
    Descrybe echoes ``state`` back verbatim on the callback.
    """
    oauth = _oauth_client()
    metadata = oauth.discover_metadata()
    redirect_uri = _redirect_uri()

    registration = oauth.register_client(
        metadata,
        redirect_uri=redirect_uri,
        client_name=settings.descrybe_client_name,
        provider="other",
    )

    code_verifier = create_code_verifier()
    state_token = _sign_state({
        "code_verifier": code_verifier,
        "client_id": registration.client_id,
        "client_secret": registration.client_secret,
        "redirect_uri": redirect_uri,
        "return_to": return_to,
    })

    authorization = oauth.prepare_authorization(
        metadata=metadata,
        client_id=registration.client_id,
        redirect_uri=redirect_uri,
        state=state_token,
        code_verifier=code_verifier,
    )

    return {
        "authorization_url": authorization.authorization_url,
    }


def exchange_code(state_token: str, code: str) -> tuple[TokenSet, dict]:
    """Exchange an OAuth authorization code for tokens.

    ``state_token`` is the encrypted bundle echoed back by Descrybe. Returns
    ``(token_set, bundle)`` so the caller can read ``return_to``.
    """
    bundle = _unsign_state(state_token)
    if bundle is None:
        raise ValueError("Missing or expired OAuth state — restart the connection flow")

    oauth = _oauth_client()
    metadata = oauth.discover_metadata()

    registration = OAuthClientRegistration(
        client_id=bundle["client_id"],
        client_secret=bundle.get("client_secret"),
        token_endpoint_auth_method="client_secret_post" if bundle.get("client_secret") else "none",
    )

    token_set = oauth.exchange_code(
        metadata=metadata,
        client=registration,
        code=code,
        redirect_uri=bundle["redirect_uri"],
        code_verifier=bundle["code_verifier"],
    )
    return token_set, bundle


# ---------------------------------------------------------------------------
# Encrypted state bundle (stateless across Fly instances — carried by browser)
# ---------------------------------------------------------------------------
def _sign_state(bundle: dict) -> str:
    """Encrypt the OAuth state (incl. PKCE code_verifier) for the round-trip.

    Uses Fernet (authenticated encryption, already a dependency) when
    DESCRYBE_TOKEN_KEY is set; falls back to plain base64 otherwise. Adds a
    10-minute expiry.
    """
    bundle = {**bundle, "exp": int(time.time()) + 600}
    payload = json.dumps(bundle, sort_keys=True).encode()
    f = _fernet()
    if f is None:
        return "b64:" + base64.urlsafe_b64encode(payload).decode()
    return "fernet:" + f.encrypt(payload).decode()


def _unsign_state(token: str) -> dict | None:
    """Decrypt + validate a state bundle, enforcing the 10-minute expiry."""
    f = _fernet()
    try:
        if token.startswith("fernet:") and f is not None:
            payload = f.decrypt(token[len("fernet:"):].encode())
        elif token.startswith("b64:"):
            payload = base64.urlsafe_b64decode(token[len("b64:"):].encode())
        else:
            return None
        bundle = json.loads(payload.decode())
    except Exception:
        return None
    if not isinstance(bundle, dict):
        return None
    if int(bundle.get("exp", 0)) < time.time():
        return None
    return bundle
