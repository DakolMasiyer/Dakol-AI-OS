from fastapi import HTTPException
from typing import Dict, Any

def enforce_immutable_approvals(request_payload: Dict[str, Any]):
    """
    Prevents frontend from directly mutating workflows or bypassing
    governance approval layers.
    """
    if "override_approval" in request_payload or "mutate_workflow" in request_payload:
        raise HTTPException(
            status_code=403, 
            detail="Frontend safety policy violation: Direct workflow mutation is strictly prohibited."
        )

def validate_cross_app_access(user_role: str, target_app: str):
    """
    Ensures that an app-scoped session cannot trigger another app's
    operational workflows without proper authorization.
    """
    # For now, simplistic check. Can be expanded with DB lookup or JWT claims.
    if user_role == "worldcup_only" and target_app != "worldcup":
        raise HTTPException(
            status_code=403,
            detail=f"Cross-app access denied for app: {target_app}"
        )
