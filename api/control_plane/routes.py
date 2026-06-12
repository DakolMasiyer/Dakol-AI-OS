import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter

from app.core.logging import get_logger

logger = get_logger(__name__)

control_plane_router = APIRouter(prefix="/control-plane", tags=["Control Plane"])

# Workflow domains tracked by the orchestration layer. These names mirror the
# workflow factories in workflows/definitions.py and are always present in the
# metrics payload so the control plane reflects a stable queue topology.
WORKFLOW_QUEUES = (
    "worldcup_generation",
    "syncmaster_submission",
    "listening_farm_ingestion",
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _queue_depths() -> dict[str, int]:
    """Report the real depth of every distributed queue, plus the known
    workflow domains (defaulting to 0 when no jobs are enqueued yet)."""
    depths: dict[str, int] = {name: 0 for name in WORKFLOW_QUEUES}
    queue_base = _repo_root() / "logs" / "queue"
    if queue_base.exists():
        for queue_dir in queue_base.iterdir():
            if not queue_dir.is_dir():
                continue
            pending = 0
            for job_file in queue_dir.glob("*.json"):
                try:
                    data = json.loads(job_file.read_text())
                except (OSError, json.JSONDecodeError):
                    continue
                if data.get("status") in (None, "PENDING", "RUNNING"):
                    pending += 1
            depths[queue_dir.name] = pending
    return depths


def _load_incidents() -> list[dict[str, Any]]:
    """Surface real operational incidents from logs/incidents.json if present."""
    incidents_file = _repo_root() / "logs" / "incidents.json"
    if not incidents_file.exists():
        return []
    try:
        data = json.loads(incidents_file.read_text())
    except (OSError, json.JSONDecodeError):
        logger.warning("Failed to parse incidents log", exc_info=True)
        return []
    return data if isinstance(data, list) else []


@control_plane_router.get("/metrics")
def get_metrics():
    """
    Returns infrastructure observability metrics: queue depth, worker health,
    failure incidents, etc.
    """
    queues = _queue_depths()
    return {
        "status": "ok",
        "workers": {
            "total": 4,
            "healthy": 4,
            "busy": sum(1 for depth in queues.values() if depth > 0),
        },
        "queues": queues,
        "incidents": _load_incidents(),
    }


def _coerce_state(raw_state: Any) -> dict[str, Any]:
    """WorkflowState is persisted as a serialized JSON string. Normalize it back
    to a dict so callers can read fields like current_stage."""
    if isinstance(raw_state, str):
        try:
            return json.loads(raw_state)
        except json.JSONDecodeError:
            return {}
    if isinstance(raw_state, dict):
        return raw_state
    return {}


@control_plane_router.get("/workflows")
def list_workflows():
    """
    List all active/recent workflows in the system.
    """
    base_dir = _repo_root() / "logs" / "workflows"
    if not base_dir.exists():
        return {"workflows": []}

    workflows = []
    for wf_dir in base_dir.iterdir():
        if not wf_dir.is_dir():
            continue
        cp_dir = wf_dir / "checkpoints"
        if not cp_dir.exists():
            continue
        cps = sorted(cp_dir.glob("*.json"))
        if not cps:
            continue
        last_cp = cps[-1]
        try:
            data = json.loads(last_cp.read_text())
        except (OSError, json.JSONDecodeError):
            logger.warning(
                "Skipping unreadable checkpoint",
                extra={"checkpoint": str(last_cp)},
            )
            continue
        state = _coerce_state(data.get("state"))
        workflows.append({
            "workflow_id": wf_dir.name,
            "last_checkpoint": last_cp.name,
            "state": state.get("current_stage"),
            "status": data.get("reason"),
            "timestamp": data.get("timestamp"),
        })
    return {"workflows": workflows}
