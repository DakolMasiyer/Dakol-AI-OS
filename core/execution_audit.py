from __future__ import annotations

import dataclasses
import hashlib
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
TRACE_DIR = BASE_DIR / "logs" / "execution"
AUDIT_LEDGER_FILE = TRACE_DIR / "audit_ledger.jsonl"
TRACE_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class ExecutionSnapshot:
    schema_version: int
    execution_id: str
    task: str
    input_payload: dict[str, Any]
    route_decision: dict[str, Any]
    selected_model: str
    selected_agent: str
    execution_timestamps: dict[str, Any]
    invariant_checks: dict[str, Any]
    output: Any
    output_hash: str
    route_fingerprint: str
    invariant_fingerprint: str
    execution_result_hash: str
    execution_fingerprint: str
    status: str
    failure_reason: str | None = None
    request_id: str | None = None
    workflow_id: str | None = None
    best_agent: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExecutionSnapshot":
        return cls(
            schema_version=int(data.get("schema_version", TRACE_SCHEMA_VERSION)),
            execution_id=str(data["execution_id"]),
            task=str(data.get("task", "")),
            input_payload=dict(data.get("input_payload", {})),
            route_decision=dict(data.get("route_decision", {})),
            selected_model=str(data.get("selected_model", "")),
            selected_agent=str(data.get("selected_agent", "")),
            execution_timestamps=dict(data.get("execution_timestamps", {})),
            invariant_checks=dict(data.get("invariant_checks", {})),
            output=data.get("output"),
            output_hash=str(data.get("output_hash", "")),
            route_fingerprint=str(data.get("route_fingerprint", "")),
            invariant_fingerprint=str(data.get("invariant_fingerprint", "")),
            execution_result_hash=str(data.get("execution_result_hash", "")),
            execution_fingerprint=str(data.get("execution_fingerprint", "")),
            status=str(data.get("status", "unknown")),
            failure_reason=data.get("failure_reason"),
            request_id=data.get("request_id"),
            workflow_id=data.get("workflow_id"),
            best_agent=data.get("best_agent"),
        )


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_json_dumps(value: Any) -> str:
    return json.dumps(_normalize(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def stable_hash(value: Any) -> str:
    payload = stable_json_dumps(value).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def build_route_fingerprint(route_decision: dict[str, Any] | None) -> str:
    if not route_decision:
        return stable_hash({})

    fields = {
        "model": route_decision.get("model", ""),
        "intent": route_decision.get("intent", ""),
        "confidence": route_decision.get("confidence", 0.0),
        "route": route_decision.get("route", ""),
        "execution_target": route_decision.get("execution_target", ""),
        "scoring_method": route_decision.get("scoring_method", ""),
        "embedding_provider": route_decision.get("embedding_provider", ""),
        "matched_terms": route_decision.get("matched_terms", []),
        "learning_applied": route_decision.get("learning_applied", False),
    }
    return stable_hash(fields)


def build_invariant_fingerprint(invariant_checks: dict[str, Any] | None) -> str:
    return stable_hash(invariant_checks or {})


def build_execution_result_hash(output: Any, agent_result: dict[str, Any] | None) -> str:
    payload = {
        "output": output,
        "agent_result": agent_result or {},
    }
    return stable_hash(payload)


def build_execution_fingerprint(
    input_payload: dict[str, Any],
    route_fingerprint: str,
    selected_model: str,
    selected_agent: str,
    invariant_fingerprint: str,
    execution_result_hash: str,
) -> str:
    return stable_hash(
        {
            "input_payload": input_payload,
            "route_fingerprint": route_fingerprint,
            "selected_model": selected_model,
            "selected_agent": selected_agent,
            "invariant_fingerprint": invariant_fingerprint,
            "execution_result_hash": execution_result_hash,
        }
    )


def create_execution_snapshot(
    *,
    execution_id: str,
    task: str,
    input_payload: dict[str, Any],
    route_decision: dict[str, Any] | None,
    selected_model: str,
    selected_agent: str,
    execution_timestamps: dict[str, Any],
    invariant_checks: dict[str, Any],
    output: Any,
    agent_result: dict[str, Any] | None,
    status: str,
    failure_reason: str | None = None,
    request_id: str | None = None,
    workflow_id: str | None = None,
    best_agent: str | None = None,
) -> ExecutionSnapshot:
    route_fingerprint = build_route_fingerprint(route_decision)
    invariant_fingerprint = build_invariant_fingerprint(invariant_checks)
    output_hash = stable_hash(output)
    execution_result_hash = build_execution_result_hash(output, agent_result)
    execution_fingerprint = build_execution_fingerprint(
        input_payload=input_payload,
        route_fingerprint=route_fingerprint,
        selected_model=selected_model,
        selected_agent=selected_agent,
        invariant_fingerprint=invariant_fingerprint,
        execution_result_hash=execution_result_hash,
    )
    return ExecutionSnapshot(
        schema_version=TRACE_SCHEMA_VERSION,
        execution_id=execution_id,
        task=task,
        input_payload=input_payload,
        route_decision=route_decision or {},
        selected_model=selected_model,
        selected_agent=selected_agent,
        execution_timestamps=execution_timestamps,
        invariant_checks=invariant_checks,
        output=output,
        output_hash=output_hash,
        route_fingerprint=route_fingerprint,
        invariant_fingerprint=invariant_fingerprint,
        execution_result_hash=execution_result_hash,
        execution_fingerprint=execution_fingerprint,
        status=status,
        failure_reason=failure_reason,
        request_id=request_id,
        workflow_id=workflow_id,
        best_agent=best_agent,
    )


def write_execution_trace(snapshot: ExecutionSnapshot, trace_dir: Path | None = None) -> Path:
    directory = Path(trace_dir) if trace_dir else TRACE_DIR
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{snapshot.execution_id}.json"
    if path.exists():
        raise FileExistsError(f"Execution trace already exists: {path}")
    path.write_text(json.dumps(snapshot.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
    return path


def load_execution_trace(path_or_execution_id: str | os.PathLike[str], trace_dir: Path | None = None) -> ExecutionSnapshot:
    candidate = Path(path_or_execution_id)
    if not candidate.exists():
        base = Path(trace_dir) if trace_dir else TRACE_DIR
        candidate = base / f"{path_or_execution_id}.json"
    data = json.loads(candidate.read_text(encoding="utf-8"))
    return ExecutionSnapshot.from_dict(data)


def list_execution_traces(trace_dir: Path | None = None) -> list[Path]:
    directory = Path(trace_dir) if trace_dir else TRACE_DIR
    if not directory.exists():
        return []
    return sorted(path for path in directory.glob("*.json") if path.is_file())


def append_audit_ledger(snapshot: ExecutionSnapshot, certification_status: str, trace_dir: Path | None = None) -> Path:
    directory = Path(trace_dir) if trace_dir else TRACE_DIR
    directory.mkdir(parents=True, exist_ok=True)
    payload = {
        "execution_id": snapshot.execution_id,
        "execution_fingerprint": snapshot.execution_fingerprint,
        "route_fingerprint": snapshot.route_fingerprint,
        "invariant_fingerprint": snapshot.invariant_fingerprint,
        "result_hash": snapshot.execution_result_hash,
        "status": certification_status,
        "recorded_at": utc_now(),
    }
    with (directory / "audit_ledger.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")
    return directory / "audit_ledger.jsonl"


def verify_replay(snapshot: ExecutionSnapshot, replay_result: dict[str, Any]) -> dict[str, Any]:
    replay_route = replay_result.get("route_decision") or {}
    replay_output = replay_result.get("output")
    replay_agent_result = replay_result.get("agent_result") or {}
    replay_invariants = replay_result.get("invariant_checks") or {}
    replay_selected_model = str(replay_result.get("selected_model", ""))
    replay_selected_agent = str(replay_result.get("selected_agent", ""))

    replay_route_fingerprint = build_route_fingerprint(replay_route)
    replay_invariant_fingerprint = build_invariant_fingerprint(replay_invariants)
    replay_output_hash = stable_hash(replay_output)
    replay_result_hash = build_execution_result_hash(replay_output, replay_agent_result)
    replay_execution_fingerprint = build_execution_fingerprint(
        input_payload=snapshot.input_payload,
        route_fingerprint=replay_route_fingerprint,
        selected_model=replay_selected_model,
        selected_agent=replay_selected_agent,
        invariant_fingerprint=replay_invariant_fingerprint,
        execution_result_hash=replay_result_hash,
    )

    comparisons = {
        "output_hash": snapshot.output_hash == replay_output_hash,
        "route_fingerprint": snapshot.route_fingerprint == replay_route_fingerprint,
        "invariant_fingerprint": snapshot.invariant_fingerprint == replay_invariant_fingerprint,
        "execution_result_hash": snapshot.execution_result_hash == replay_result_hash,
        "execution_fingerprint": snapshot.execution_fingerprint == replay_execution_fingerprint,
    }
    status = "VERIFIED" if all(comparisons.values()) else "DEGRADED"
    return {
        "status": status,
        "comparisons": comparisons,
        "snapshot": snapshot.to_dict(),
        "replay": {
            "route_fingerprint": replay_route_fingerprint,
            "invariant_fingerprint": replay_invariant_fingerprint,
            "output_hash": replay_output_hash,
            "execution_result_hash": replay_result_hash,
            "execution_fingerprint": replay_execution_fingerprint,
        },
    }


def classify_certification(snapshot: ExecutionSnapshot, replay_verdict: dict[str, Any] | None = None) -> str:
    if snapshot.status == "failed" or snapshot.failure_reason:
        return "CONTRACT VIOLATION"
    invariant_values = snapshot.invariant_checks.values()
    if invariant_values and not all(bool(value) for value in invariant_values):
        return "DEGRADED"
    if replay_verdict is not None and replay_verdict.get("status") != "VERIFIED":
        return "NON-DETERMINISTIC"
    return "VERIFIED"


def _normalize(value: Any) -> Any:
    if dataclasses.is_dataclass(value):
        return {key: _normalize(val) for key, val in dataclasses.asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): _normalize(val) for key, val in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, tuple):
        return [_normalize(item) for item in value]
    if isinstance(value, set):
        return sorted(_normalize(item) for item in value)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value
