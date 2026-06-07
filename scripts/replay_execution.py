from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.api import execute_task, load_execution_trace, verify_replay


def replay_trace(trace_path: str | os.PathLike[str], repeat: int = 1) -> dict:
    snapshot = load_execution_trace(trace_path)
    results = []
    for _ in range(repeat):
        replay_result = execute_task(
            snapshot.task,
            record_memory=False,
            record_trace=False,
            capture_metadata=True,
        )
        results.append(verify_replay(snapshot, replay_result))

    overall_status = "VERIFIED" if all(result["status"] == "VERIFIED" for result in results) else "DEGRADED"
    return {
        "status": overall_status,
        "trace_path": str(trace_path),
        "execution_id": snapshot.execution_id,
        "replays": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Replay and verify a recorded execution trace.")
    parser.add_argument("trace_path", help="Path to a trace JSON file or an execution_id")
    parser.add_argument("--repeat", type=int, default=1, help="Number of deterministic replays to run")
    args = parser.parse_args(argv)

    result = replay_trace(args.trace_path, repeat=max(1, args.repeat))
    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0 if result["status"] == "VERIFIED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
