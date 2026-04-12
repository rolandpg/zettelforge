"""
ThreatRecall Authentication — OAuth/OIDC + JWT + Multi-tenant isolation.

Supports: Google, GitHub, Microsoft (add Apple via config).
Uses Authlib for OIDC flows, PyJWT for token issuance, HTTP-only cookies for storage.

Setup:
    1. Create OAuth apps at each provider (get client_id + client_secret)
    2. Set env vars: OAUTH_GOOGLE_CLIENT_ID, OAUTH_GOOGLE_CLIENT_SECRET, etc.
    3. Set JWT_SECRET (random 32+ char string)
    4. Set THREATRECALL_BASE_URL (e.g., https://threatrecall.example.com)

Architecture:
    /auth/login/{provider}  → Redirects to OAuth provider
    /auth/callback          → Handles OAuth callback, issues JWT in HTTP-only cookie
    /auth/logout            → Clears cookie
    /auth/me                → Returns current user info from JWT

    Every API endpoint checks the JWT cookie. The tenant_id in the JWT
    determines which MemoryManager instance (and data directory) is used.
"""
import os
import uuid
import time
import hashlib
import jwt
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict
from functools import wraps

from fastapi import Request, Response, HTTPException
from fastapi.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth


# ── Configuration ────────────────────────────────────────────────────────────

JWT_SECRET = os.environ.get("JWT_SECRET", "")
if not JWT_SECRET:
    import warnings
    JWT_SECRET = "threatrecall-dev-insecure-DO-NOT-USE-IN-PRODUCTION"
    warnings.warn(
        "JWT_SECRET is not set. Using an insecure default. "
        "Set the JWT_SECRET environment variable before deploying to production.",
        stacklevel=1,
    )
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = int(os.environ.get("JWT_EXPIRY_HOURS", "24"))
BASE_URL = os.environ.get("THREATRECALL_BASE_URL", "http://localhost:8088")
COOKIE_NAME = "threatrecall_session"
COOKIE_SECURE = os.environ.get("THREATRECALL_COOKIE_SECURE", "false").lower() == "true"

# Multi-tenant data root
TENANT_DATA_ROOT = Path(os.environ.get(
    "THREATRECALL_TENANT_ROOT",
    os.path.expanduser("~/.amem/tenants")
))


# ── OAuth Setup ──────────────────────────────────────────────────────────────

oauth = OAuth()

# Google
if os.environ.get("OAUTH_GOOGLE_CLIENT_ID"):
    oauth.register(
        name="google",
        client_id=os.environ["OAUTH_GOOGLE_CLIENT_ID"],
        client_secret=os.environ["OAUTH_GOOGLE_CLIENT_SECRET"],
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )

# GitHub
if os.environ.get("OAUTH_GITHUB_CLIENT_ID"):
    oauth.register(
        name="github",
        client_id=os.environ["OAUTH_GITHUB_CLIENT_ID"],
        client_secret=os.environ["OAUTH_GITHUB_CLIENT_SECRET"],
        access_token_url="https://github.com/login/oauth/access_token",
        authorize_url="https://github.com/login/oauth/authorize",
        api_base_url="https://api.github.com/",
        client_kwargs={"scope": "user:email"},
    )

# Microsoft
if os.environ.get("OAUTH_MICROSOFT_CLIENT_ID"):
    oauth.register(
        name="microsoft",
        client_id=os.environ["OAUTH_MICROSOFT_CLIENT_ID"],
        client_secret=os.environ["OAUTH_MICROSOFT_CLIENT_SECRET"],
        server_metadata_url="https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )


# ── JWT Token Management ────────────────────────────────────────────────────

def create_jwt(user_info: Dict) -> str:
    """Create a JWT token with user info and tenant_id."""
    # Derive tenant_id from email (deterministic, stable)
    email = user_info.get("email", "anonymous")
    tenant_id = hashlib.sha256(email.encode()).hexdigest()[:16]

    payload = {
        "sub": email,
        "name": user_info.get("name", email.split("@")[0]),
        "picture": user_info.get("picture", ""),
        "provider": user_info.get("provider", "unknown"),
        "tenant_id": tenant_id,
        "iat": int(time.time()),
        "exp": int(time.time()) + (JWT_EXPIRY_HOURS * 3600),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_jwt(token: str) -> Optional[Dict]:
    """Decode and validate a JWT token."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_current_user(request: Request) -> Optional[Dict]:
    """Extract user from JWT cookie. Returns None if not authenticated."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    return decode_jwt(token)


def require_auth(request: Request) -> Dict:
    """Require authentication. Raises 401 if not logged in."""
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


# ── Multi-Tenant Memory Manager ─────────────────────────────────────────────

_tenant_managers: Dict[str, object] = {}


def get_tenant_mm(tenant_id: str):
    """Get or create a MemoryManager for a specific tenant."""
    if tenant_id not in _tenant_managers:
        from zettelforge import MemoryManager

        tenant_dir = TENANT_DATA_ROOT / tenant_id
        tenant_dir.mkdir(parents=True, exist_ok=True)

        _tenant_managers[tenant_id] = MemoryManager(
            jsonl_path=str(tenant_dir / "notes.jsonl"),
            lance_path=str(tenant_dir / "vectordb"),
        )
    return _tenant_managers[tenant_id]


def get_mm_for_request(request: Request):
    """Get the MemoryManager for the authenticated user's tenant."""
    user = get_current_user(request)
    if user:
        return get_tenant_mm(user["tenant_id"])

    # Unauthenticated: use default (single-tenant mode)
    from zettelforge import MemoryManager
    if "default" not in _tenant_managers:
        _tenant_managers["default"] = MemoryManager()
    return _tenant_managers["default"]


# ── Auth Routes ──────────────────────────────────────────────────────────────

def register_auth_routes(app):
    """Register OAuth routes on a FastAPI app."""
    from starlette.middleware.sessions import SessionMiddleware
    app.add_middleware(
        SessionMiddleware,
        secret_key=JWT_SECRET,
        session_cookie="threatrecall_oauth_state",
        max_age=600,  # 10 min for OAuth flow
        https_only=COOKIE_SECURE,
    )

    @app.get("/auth/login/{provider}")
    async def login(request: Request, provider: str):
        """Redirect to OAuth provider."""
        client = oauth.create_client(provider)
        if not client:
            raise HTTPException(400, f"Provider '{provider}' not configured")
        redirect_uri = f"{BASE_URL}/auth/callback?provider={provider}"
        return await client.authorize_redirect(request, redirect_uri)

    @app.get("/auth/callback")
    async def callback(request: Request):
        """Handle OAuth callback, issue JWT in HTTP-only cookie."""
        provider = request.query_params.get("provider", "google")
        client = oauth.create_client(provider)
        if not client:
            raise HTTPException(400, f"Provider '{provider}' not configured")

        token = await client.authorize_access_token(request)

        # Get user info
        if provider == "github":
            resp = await client.get("user", token=token)
            profile = resp.json()
            # GitHub doesn't return email in profile, fetch separately
            email_resp = await client.get("user/emails", token=token)
            emails = email_resp.json()
            primary_email = next((e["email"] for e in emails if e["primary"]), profile.get("login"))
            user_info = {
                "email": primary_email,
                "name": profile.get("name", profile.get("login")),
                "picture": profile.get("avatar_url", ""),
                "provider": "github",
            }
        else:
            # Google, Microsoft — standard OIDC
            user_info_data = token.get("userinfo", {})
            if not user_info_data:
                user_info_data = await client.userinfo(token=token)
            user_info = {
                "email": user_info_data.get("email", ""),
                "name": user_info_data.get("name", ""),
                "picture": user_info_data.get("picture", ""),
                "provider": provider,
            }

        # Create JWT
        jwt_token = create_jwt(user_info)

        # Set HTTP-only cookie and redirect to app
        response = RedirectResponse(url="/")
        response.set_cookie(
            key=COOKIE_NAME,
            value=jwt_token,
            httponly=True,           # Not accessible via JavaScript
            secure=COOKIE_SECURE,    # HTTPS only in production
            samesite="lax",          # CSRF protection
            max_age=JWT_EXPIRY_HOURS * 3600,
        )
        return response

    @app.get("/auth/logout")
    async def logout():
        """Clear auth cookie."""
        response = RedirectResponse(url="/")
        response.delete_cookie(COOKIE_NAME)
        return response

    @app.get("/auth/me")
    async def me(request: Request):
        """Return current user info from JWT."""
        user = get_current_user(request)
        if not user:
            return {"authenticated": False}
        return {
            "authenticated": True,
            "email": user.get("sub"),
            "name": user.get("name"),
            "picture": user.get("picture"),
            "provider": user.get("provider"),
            "tenant_id": user.get("tenant_id"),
        }

    @app.get("/auth/providers")
    async def providers():
        """List configured OAuth providers."""
        available = []
        if os.environ.get("OAUTH_GOOGLE_CLIENT_ID"):
            available.append("google")
        if os.environ.get("OAUTH_GITHUB_CLIENT_ID"):
            available.append("github")
        if os.environ.get("OAUTH_MICROSOFT_CLIENT_ID"):
            available.append("microsoft")
        return {"providers": available}
