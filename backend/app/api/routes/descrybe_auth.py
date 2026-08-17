"""
Legal AI OS — Descrybe OAuth Routes

Hosts the in-app "Connect Descrybe" flow. No static API key: the user approves
the app against their own Descrybe account, and the backend stores the resulting
refresh token (encrypted) so it can call the Descrybe Legal Engine on their behalf.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse

from app.auth import get_current_user, User
from app.services import descrybe_oauth

router = APIRouter()


@router.get("/connect")
async def connect(
    return_to: str | None = Query(default=None),
    user: User = Depends(get_current_user),
):
    """Start the OAuth flow. Returns the Descrybe authorization URL to redirect to."""
    try:
        return descrybe_oauth.build_connect(user.id, return_to=return_to)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Descrybe connection failed: {str(e)}")


@router.get("/callback")
async def callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    user: User = Depends(get_current_user),
):
    """Handle Descrybe's redirect back after the user approves the connection."""
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")
    if not state:
        raise HTTPException(status_code=400, detail="Missing OAuth state")

    try:
        token_set, bundle = descrybe_oauth.exchange_code(state, code)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OAuth exchange failed: {str(e)}")

    descrybe_oauth._upsert_connection(user.id, token_set)

    return_to = bundle.get("return_to") or "/legal-research"
    return RedirectResponse(url=return_to)


@router.get("/status")
async def status(user: User = Depends(get_current_user)):
    """Whether the current user has a live Descrybe connection."""
    return {
        "connected": descrybe_oauth.is_connected(user.id),
        "redirect_uri": descrybe_oauth._redirect_uri(),
    }


@router.post("/disconnect")
async def disconnect(user: User = Depends(get_current_user)):
    """Remove the current user's Descrybe connection."""
    descrybe_oauth.disconnect(user.id)
    return {"connected": False}
