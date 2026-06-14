import os
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt import PyJWKClient, PyJWKClientError

security = HTTPBearer(auto_error=False)

def get_supabase_jwt_secret() -> str:
    return os.environ.get("SUPABASE_JWT_SECRET", "")


def _normalize_issuer(value: str) -> str:
    """Normalize a Supabase URL or issuer to the canonical issuer form
    ``https://<ref>.supabase.co/auth/v1``."""
    v = value.strip().rstrip("/")
    if not v:
        return ""
    return v if v.endswith("/auth/v1") else f"{v}/auth/v1"


def _allowed_issuers() -> set[str]:
    """Issuers whose tokens we trust: the backend's own Supabase project plus any
    configured via SUPABASE_TRUSTED_ISSUERS (e.g. the worldcup-ai frontend project,
    which is a different Supabase project and signs the end-user tokens)."""
    issuers: set[str] = set()
    base = os.environ.get("SUPABASE_URL", "")
    if base:
        issuers.add(_normalize_issuer(base))
    for extra in os.environ.get("SUPABASE_TRUSTED_ISSUERS", "").split(","):
        norm = _normalize_issuer(extra)
        if norm:
            issuers.add(norm)
    return issuers


# Modern Supabase projects sign access tokens with asymmetric keys (ES256) and
# publish the public keys via JWKS. We verify each token against ITS OWN issuer's
# JWKS (so a multi-project setup works), but only for issuers on the allowlist.
# One client is cached per issuer; the client caches the fetched key set itself.
_jwk_clients: Dict[str, PyJWKClient] = {}


def _jwk_client_for(issuer: str) -> PyJWKClient:
    client = _jwk_clients.get(issuer)
    if client is None:
        client = PyJWKClient(f"{issuer}/.well-known/jwks.json")
        _jwk_clients[issuer] = client
    return client


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

    # Inspect the token (unverified) to pick the right verification path.
    # alg → key material; iss → which project's JWKS to use.
    try:
        alg = jwt.get_unverified_header(token).get("alg", "")
        issuer = (jwt.decode(token, options={"verify_signature": False}).get("iss") or "").rstrip("/")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        if alg.startswith("ES") or alg.startswith("RS"):
            # Asymmetric: keys are fetched from the issuer's URL, so the issuer
            # MUST be pinned to the allowlist to prevent impersonation via a
            # token signed by an attacker-controlled Supabase project.
            allowed = _allowed_issuers()
            if not issuer or (allowed and issuer not in allowed):
                raise HTTPException(status_code=401, detail="Untrusted token issuer")
            signing_key = _jwk_client_for(issuer).get_signing_key_from_jwt(token).key
            return jwt.decode(
                token,
                signing_key,
                algorithms=[alg],
                audience="authenticated",
                issuer=issuer,
            )

        # Legacy HS256 path — the shared secret already binds the token to a
        # known project, so no separate issuer pin is required here.
        secret = get_supabase_jwt_secret()
        if not secret and os.environ.get("ENVIRONMENT") != "production":
            # Dev convenience: decode without verification when no secret is set.
            return jwt.decode(token, options={"verify_signature": False})
        return jwt.decode(token, secret, algorithms=["HS256"], audience="authenticated")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except (jwt.InvalidTokenError, PyJWKClientError):
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
