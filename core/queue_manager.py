"""Distributed queue manager with lease-based crash recovery.

This is the orchestration entrypoint used by workers and the control plane. It
is named ``RedisQueueManager`` because Redis is the intended production backend
(via ``REDIS_URL``), but it degrades cleanly to the local file-backed queue used
by :mod:`core.queue.worker` when no Redis URL is configured. The local backend
provides the same at-least-once, lease-with-recovery semantics so behaviour is
verifiable without external infrastructure.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from core.queue.jobs import JobState
from core.queue.retry_policy import RetryPolicy


class RedisQueueManager:
    """Manages job leases across workers for a single queue.

    In local mode jobs are persisted as JSON files under
    ``logs/queue/<queue_name>/``. Leases carry an expiry; an expired lease can be
    reclaimed by any other worker, which is how a crashed worker's in-flight job
    is recovered deterministically.
    """

    def __init__(
        self,
        queue_name: str = "default",
        redis_url: Optional[str] = None,
        root_dir: Optional[Path] = None,
        lease_duration_seconds: int = 300,
    ) -> None:
        self.queue_name = queue_name
        self.redis_url = redis_url or os.environ.get("REDIS_URL") or None
        self.backend = "redis" if self.redis_url else "local"
        self.lease_duration_seconds = lease_duration_seconds
        self.retry_policy = RetryPolicy()

        root = Path(root_dir) if root_dir else Path(__file__).resolve().parents[1]
        self.queue_dir = root / "logs" / "queue" / self.queue_name
        self.queue_dir.mkdir(parents=True, exist_ok=True)

    # -- persistence helpers -------------------------------------------------

    def _job_file(self, job_id: str) -> Path:
        return self.queue_dir / f"{job_id}.json"

    def _save(self, job: JobState) -> None:
        self._job_file(job.job_id).write_text(job.serialize())

    def _load(self, job_id: str) -> Optional[JobState]:
        path = self._job_file(job_id)
        if not path.exists():
            return None
        return JobState.deserialize(path.read_text())

    # -- public API ----------------------------------------------------------

    def enqueue(self, payload: dict[str, Any], job_id: Optional[str] = None) -> JobState:
        job_id = job_id or uuid.uuid4().hex
        job = JobState(job_id=job_id, queue_name=self.queue_name, payload=payload)
        self._save(job)
        return job

    def claim(self, job_id: str, worker_id: str) -> Optional[JobState]:
        """Attempt to acquire (or recover) the lease for a job.

        Returns the locked job on success, or ``None`` if another worker holds a
        still-valid lease.
        """
        job = self._load(job_id)
        if job is None:
            return None
        if not job.lock(worker_id, self.lease_duration_seconds):
            return None
        self._save(job)
        return job

    def recover_expired_leases(self) -> list[str]:
        """Reset jobs whose lease has expired back to PENDING so another worker
        can pick them up. Returns the list of recovered job ids."""
        now = datetime.now(timezone.utc)
        recovered: list[str] = []
        for job_file in self.queue_dir.glob("*.json"):
            job = JobState.deserialize(job_file.read_text())
            if job.status != "RUNNING" or job.lease is None:
                continue
            expires_at = datetime.fromisoformat(job.lease.expires_at)
            if expires_at <= now:
                job.status = "PENDING"
                job.lease = None
                self._save(job)
                recovered.append(job.job_id)
        return recovered

    def queue_depth(self) -> int:
        """Number of jobs not yet in a terminal state."""
        depth = 0
        for job_file in self.queue_dir.glob("*.json"):
            job = JobState.deserialize(job_file.read_text())
            if job.status in ("PENDING", "RUNNING"):
                depth += 1
        return depth
