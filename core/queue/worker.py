import json
import uuid
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from core.queue.jobs import JobState
from core.queue.retry_policy import RetryPolicy
from runtime.environment import ensure_runtime_environment

class DistributedWorker:
    def __init__(self, queue_name: str, root_dir: Optional[Path] = None):
        self.runtime_manifest = ensure_runtime_environment(component="worker")
        self.worker_id = f"worker-{uuid.uuid4().hex[:8]}"
        self.queue_name = queue_name
        self.root_dir = root_dir or Path(__file__).resolve().parents[2]
        self.queue_dir = self.root_dir / "logs" / "queue" / self.queue_name
        self.queue_dir.mkdir(parents=True, exist_ok=True)
        self.handlers: Dict[str, Callable[[dict[str, Any]], Any]] = {}
        self.retry_policy = RetryPolicy()

    def register_handler(self, job_type: str, handler: Callable[[dict[str, Any]], Any]) -> None:
        self.handlers[job_type] = handler

    def enqueue(self, job_id: str, job_type: str, payload: dict[str, Any]) -> JobState:
        job = JobState(job_id=job_id, queue_name=self.queue_name, payload={"job_type": job_type, **payload})
        self._save_job(job)
        return job

    def _save_job(self, job: JobState) -> None:
        job_file = self.queue_dir / f"{job.job_id}.json"
        job_file.write_text(job.serialize())

    def _load_job(self, job_id: str) -> Optional[JobState]:
        job_file = self.queue_dir / f"{job_id}.json"
        if not job_file.exists():
            return None
        return JobState.deserialize(job_file.read_text())

    def process_job(self, job_id: str) -> None:
        job = self._load_job(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        # Try to lock
        if not job.lock(self.worker_id, lease_duration_seconds=300):
            raise RuntimeError(f"Failed to acquire lease for job {job_id}")

        self._save_job(job)

        try:
            job_type = job.payload.get("job_type")
            handler = self.handlers.get(job_type)
            if not handler:
                raise ValueError(f"No handler registered for {job_type}")

            job.attempts += 1
            handler(job.payload)

            job.mark_completed()
            self._save_job(job)
            
        except Exception as e:
            if job.attempts < self.retry_policy.max_retries:
                # Retryable failure
                job.status = "PENDING"
                job.lease = None
                job.error_history.append(str(e))
                self._save_job(job)
            else:
                job.mark_failed(str(e))
                self._save_job(job)
            raise e
