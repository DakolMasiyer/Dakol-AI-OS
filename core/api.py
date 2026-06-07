from __future__ import annotations

from pathlib import Path
from typing import Any


def route_task(task: str):
    from scripts.router import route_task as _route_task

    return _route_task(task)


from typing import Optional

def execute_task(
    task: str,
    *,
    record_memory: bool = True,
    record_trace: bool = True,
    capture_metadata: bool = False,
    app_id: Optional[str] = None,
):
    from scripts.router import execute_task as _execute_task

    return _execute_task(
        task,
        record_memory=record_memory,
        record_trace=record_trace,
        capture_metadata=capture_metadata,
        app_id=app_id,
    )


def execute_tool(
    tool_name: str,
    arguments: dict[str, Any],
    app_id: str,
) -> Any:
    from core.tool_policy import verify_tool_execution
    from tools.builtin import create_default_registry
    from datetime import datetime, timezone
    import time
    from uuid import uuid4

    # 1. Enforce Tool Governance
    verify_tool_execution(app_id, tool_name)

    # 2. Execute the tool
    registry = create_default_registry()
    started_at = datetime.now(timezone.utc)
    started_perf = time.perf_counter()
    status = "completed"
    failure_reason = None
    output = None

    try:
        output = registry.execute(tool_name, arguments)
    except Exception as exc:
        status = "failed"
        failure_reason = f"{exc.__class__.__name__}: {exc}"
        raise
    finally:
        finished_at = datetime.now(timezone.utc)
        duration_ms = int((time.perf_counter() - started_perf) * 1000)
        
        # 3. Preserve traceability & replayability
        snapshot = create_execution_snapshot(
            execution_id=f"{app_id}-{uuid4()}",
            task=f"Tool Execution: {tool_name}",
            input_payload={"tool_name": tool_name, "arguments": arguments},
            route_decision={},
            selected_model="system",
            selected_agent="tool_registry",
            execution_timestamps={
                "started_at": started_at.isoformat(),
                "finished_at": finished_at.isoformat(),
                "duration_ms": duration_ms,
            },
            invariant_checks={"tool_policy_verified": True},
            output=output,
            agent_result=None,
            status=status,
            failure_reason=failure_reason,
        )
        trace_dir = Path(__file__).resolve().parents[1] / "logs" / "execution" / app_id
        write_execution_trace(snapshot, trace_dir=trace_dir)
        
    return output


def create_execution_snapshot(**kwargs: Any):
    from core.execution_audit import create_execution_snapshot as _create_execution_snapshot

    return _create_execution_snapshot(**kwargs)


def write_execution_trace(snapshot, trace_dir: Path | None = None):
    from core.execution_audit import write_execution_trace as _write_execution_trace

    return _write_execution_trace(snapshot, trace_dir=trace_dir)


def load_execution_trace(path_or_execution_id: str | Path, trace_dir: Path | None = None):
    from core.execution_audit import load_execution_trace as _load_execution_trace

    return _load_execution_trace(path_or_execution_id, trace_dir=trace_dir)


def verify_replay(snapshot, replay_result: dict[str, Any]):
    from core.execution_audit import verify_replay as _verify_replay

    return _verify_replay(snapshot, replay_result)


def classify_certification(snapshot, replay_verdict: dict[str, Any] | None = None):
    from core.execution_audit import classify_certification as _classify_certification

    return _classify_certification(snapshot, replay_verdict)


def build_import_graph(repo_root: Path | None = None):
    from scripts.import_graph_snapshot import build_import_graph as _build_import_graph

    return _build_import_graph(repo_root)


def validate_import_graph_snapshot(snapshot: dict[str, Any], current: dict[str, Any]):
    from scripts.import_graph_snapshot import validate_snapshot as _validate_snapshot

    return _validate_snapshot(snapshot, current)


def list_execution_traces(trace_dir: Path | None = None):
    from core.execution_audit import list_execution_traces as _list_execution_traces

    return _list_execution_traces(trace_dir)


def WorkflowEngine(*args, **kwargs):
    from core.workflows import WorkflowEngine as _WorkflowEngine
    return _WorkflowEngine(*args, **kwargs)


def WorkflowPolicyEngine(*args, **kwargs):
    from core.workflow_policy import WorkflowPolicyEngine as _WorkflowPolicyEngine
    return _WorkflowPolicyEngine(*args, **kwargs)

