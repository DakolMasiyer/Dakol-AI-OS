import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.gateway.auth import require_app_auth

# The main gateway router that will be mounted on the FastAPI app (under /api).
gateway_router = APIRouter()

# Individual product routers
worldcup_router = APIRouter(prefix="/worldcup", tags=["WorldCup AI"])
syncmaster_router = APIRouter(prefix="/syncmaster", tags=["SyncMaster"])
farm_router = APIRouter(prefix="/farm", tags=["Listening Farm"])


class GatewayEvaluateRequest(BaseModel):
    track_id: Optional[str] = None
    audio_url: str = "local://test"
    synthetic: bool = True


@syncmaster_router.post("/evaluate")
def gateway_syncmaster_evaluate(
    payload: GatewayEvaluateRequest,
    user: Dict[str, Any] = Depends(require_app_auth("syncmaster")),
):
    """Authenticated gateway entrypoint for SyncMaster track evaluation.

    Auth (valid JWT scoped to the ``syncmaster`` app) is enforced before any
    work runs. The actual evaluation is delegated to the listening-farm
    ingestion workflow so behaviour matches the internal pipeline.
    """
    from workflows.definitions import create_listening_farm_ingestion_workflow

    track_id = payload.track_id or str(uuid.uuid4())
    engine = create_listening_farm_ingestion_workflow("listening_farm", workflow_id=track_id)
    res = engine.execute({
        "track_id": track_id,
        "audio_url": payload.audio_url,
        "synthetic": payload.synthetic,
    })
    if res.get("status") == "COMPLETED":
        return res.get("payload", {}).get("evaluation_result", {})
    return {"status": res.get("status"), "track_id": track_id}


# Mount product routers onto the gateway. main.py includes gateway_router under
# the /api prefix, exposing e.g. POST /api/syncmaster/evaluate.
gateway_router.include_router(worldcup_router)
gateway_router.include_router(syncmaster_router)
gateway_router.include_router(farm_router)
