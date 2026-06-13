import os
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt import PyJWKClient

security = HTTPBearer(auto_error=False)

def get_supabase_jwt_secret() -> str:
    return os.environ.get("SUPABASE_JWT_SECRET", "")


# Modern Supabase projects sign access tokens with asymmetric keys (ES256) and
# publish the public keys via JWKS. The client caches fetched keys internally,
# so we build it once at module load. Legacy projects use HS256 + the shared
# JWT secret, which we keep as a fallback below.
_jwks_client: Optional[PyJWKClient] = None


def _get_jwks_client() -> Optional[PyJWKClient]:
    global _jwks_client
    if _jwks_client is None:
        supabase_url = os.environ.get("SUPABASE_URL", "").rstrip("/")
        if not supabase_url:
            return None
        _jwks_client = PyJWKClient(f"{supabase_url}/auth/v1/.well-known/jwks.json")
    return _jwks_client

async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> Optional[Dict[str, Any]]:
    """
    Dependency to verify Supabase JWT token and extract user identity.
    Returns the decoded token payload (which includes 'sub' as user_id),
    or raises HTTPException if invalid/missing when required.
    """
    if not credentials:
        # Allow anonymous for now if no token is provided, 
        # or return None to let the endpoint decide.
        return {"sub": "anonymous", "role": "anon"}
        
    token = credentials.credentials

    # Determine the signing algorithm from the token header so we verify with
    # the right key material (ES256 via JWKS for modern Supabase projects,
    # HS256 via shared secret for legacy ones).
    try:
        alg = jwt.get_unverified_header(token).get("alg", "")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        if alg.startswith("ES") or alg.startswith("RS"):
            jwks_client = _get_jwks_client()
            if jwks_client is None:
                raise HTTPException(status_code=500, detail="Auth not configured (SUPABASE_URL missing)")
            signing_key = jwks_client.get_signing_key_from_jwt(token).key
            payload = jwt.decode(token, signing_key, algorithms=[alg], audience="authenticated")
            return payload

        # Legacy HS256 path.
        secret = get_supabase_jwt_secret()
        if not secret and os.environ.get("ENVIRONMENT") != "production":
            # Dev convenience: decode without verification when no secret is set.
            return jwt.decode(token, options={"verify_signature": False})
        payload = jwt.decode(token, secret, algorithms=["HS256"], audience="authenticated")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def require_auth(user: Optional[Dict[str, Any]] = Security(get_current_user)) -> Dict[str, Any]:
    """Strict dependency that requires a valid authenticated user."""
    if not user or user.get("sub") == "anonymous":
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


def _token_app_scopes(user: Dict[str, Any]) -> set[str]:
    """Extract the set of application scopes a token is allowed to access.

    Supports a few common claim shapes: a single ``app``/``app_id`` string, or a
    list of ``apps``/``app_ids``. A token with no scope claim is treated as
    unscoped (access to any single app it authenticates against is allowed).
    """
    scopes: set[str] = set()
    for single in ("app", "app_id"):
        value = user.get(single)
        if isinstance(value, str) and value:
            scopes.add(value)
    for plural in ("apps", "app_ids"):
        value = user.get(plural)
        if isinstance(value, (list, tuple)):
            scopes.update(str(item) for item in value if item)
    return scopes


def require_app_auth(app_id: str):
    """Build a dependency that requires an authenticated user whose token is
    scoped to ``app_id``. Enforces cross-app isolation: a token issued for one
    product cannot drive another product's workflows.
    """

    def _dependency(
        request: Request,
        user: Optional[Dict[str, Any]] = Security(get_current_user),
    ) -> Dict[str, Any]:
        if not user or user.get("sub") == "anonymous":
            raise HTTPException(status_code=401, detail="Authentication required")

        scopes = _token_app_scopes(user)
        header_app = request.headers.get("X-App-ID")

        # If the token declares app scopes, they must include this app.
        if scopes and app_id not in scopes:
            raise HTTPException(
                status_code=403,
                detail=f"Token is not authorized for app '{app_id}'",
            )

        # A declared X-App-ID must agree with both the route and the token scope.
        if header_app and header_app != app_id:
            raise HTTPException(
                status_code=403,
                detail=f"Cross-app access denied for '{header_app}'",
            )

        return user

    return _dependency
