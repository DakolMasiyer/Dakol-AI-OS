#!/usr/bin/env python3
from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from runtime.environment import ensure_runtime_environment, runtime_fingerprint


def _smoke_web() -> None:
    manifest = ensure_runtime_environment(component="web")

    from api.main import app

    assert app.state.runtime_manifest["fingerprint"] == manifest["fingerprint"]
    assert runtime_fingerprint(app.state.runtime_manifest) == app.state.runtime_manifest["fingerprint"]

    client = TestClient(app)
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}

    metrics = client.get("/api/control-plane/metrics")
    assert metrics.status_code == 200
    payload = metrics.json()
    assert payload["status"] == "ok"
    assert "workers" in payload
    assert "queues" in payload


def _smoke_worker() -> None:
    manifest = ensure_runtime_environment(component="worker")

    from core.queue.worker import DistributedWorker

    with tempfile.TemporaryDirectory() as tmp_dir:
        worker = DistributedWorker(queue_name="smoke", root_dir=Path(tmp_dir))
        assert worker.runtime_manifest["fingerprint"] == manifest["fingerprint"]
        assert worker.runtime_manifest["python_major_minor"] == "3.11"
        assert worker.queue_dir.exists()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Runtime smoke checks for Dakol-AI-OS")
    parser.add_argument(
        "--component",
        choices=("web", "worker", "both"),
        default="both",
        help="Which startup surface to verify.",
    )
    args = parser.parse_args(argv)

    if args.component in {"web", "both"}:
        _smoke_web()
    if args.component in {"worker", "both"}:
        _smoke_worker()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
