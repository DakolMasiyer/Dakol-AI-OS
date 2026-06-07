from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.execution_audit import ExecutionSnapshot, list_execution_traces, load_execution_trace


REQUIRED_FIELDS = {
    "schema_version",
    "execution_id",
    "task",
    "input_payload",
    "route_decision",
    "selected_model",
    "selected_agent",
    "execution_timestamps",
    "invariant_checks",
    "output_hash",
    "route_fingerprint",
    "invariant_fingerprint",
    "execution_result_hash",
    "execution_fingerprint",
    "status",
}


def validate_trace_data(data: dict[str, Any]) -> list[str]:
    issues = []
    missing = sorted(REQUIRED_FIELDS - set(data))
    if missing:
        issues.append(f"missing fields: {', '.join(missing)}")

    for key in ("output_hash", "route_fingerprint", "invariant_fingerprint", "execution_result_hash", "execution_fingerprint"):
        value = str(data.get(key, ""))
        if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
            issues.append(f"{key} is not a valid sha256 hex digest")

    timestamps = data.get("execution_timestamps", {})
    if not isinstance(timestamps, dict):
        issues.append("execution_timestamps must be an object")
    else:
        for key in ("started_at", "finished_at", "duration_ms"):
            if key not in timestamps:
                issues.append(f"execution_timestamps missing {key}")

    invariants = data.get("invariant_checks", {})
    if not isinstance(invariants, dict) or not invariants:
        issues.append("invariant_checks must be a non-empty object")
    else:
        for name, value in invariants.items():
            if not isinstance(value, bool):
                issues.append(f"invariant_checks.{name} must be boolean")

    if data.get("status") not in {"completed", "failed"}:
        issues.append("status must be completed or failed")

    return issues


def validate_trace_file(path: Path) -> list[str]:
    data = load_execution_trace(path).to_dict()
    issues = validate_trace_data(data)
    if not data.get("execution_fingerprint"):
        issues.append("execution_fingerprint missing")
    return issues


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate execution traces.")
    parser.add_argument("--trace-dir", default=None, help="Optional directory containing trace JSON files")
    args = parser.parse_args(argv)

    trace_dir = Path(args.trace_dir) if args.trace_dir else None
    traces = list_execution_traces(trace_dir)
    issues = {}
    for trace in traces:
        trace_issues = validate_trace_file(trace)
        if trace_issues:
            issues[str(trace)] = trace_issues

    result = {
        "trace_count": len(traces),
        "status": "VERIFIED" if not issues else "DEGRADED",
        "issues": issues,
    }
    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
