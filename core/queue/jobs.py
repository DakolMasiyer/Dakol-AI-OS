import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Optional

@dataclass
class JobLease:
    worker_id: str
    expires_at: str

@dataclass
class JobState:
    job_id: str
    queue_name: str
    payload: dict[str, Any]
    status: str = "PENDING"  # PENDING, RUNNING, COMPLETED, FAILED
    attempts: int = 0
    lease: Optional[JobLease] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    error_history: list[str] = field(default_factory=list)

    def serialize(self) -> str:
        return json.dumps(asdict(self), sort_keys=True)

    @classmethod
    def deserialize(cls, data: str) -> "JobState":
        parsed = json.loads(data)
        if parsed.get("lease"):
            parsed["lease"] = JobLease(**parsed["lease"])
        return cls(**parsed)

    def lock(self, worker_id: str, lease_duration_seconds: int) -> bool:
        now = datetime.now(timezone.utc)
        if self.lease:
            expires_at = datetime.fromisoformat(self.lease.expires_at)
            if expires_at > now and self.lease.worker_id != worker_id:
                # Job is locked by another worker and lease is still valid
                return False

        # Acquire lock
        expiration = now.timestamp() + lease_duration_seconds
        self.lease = JobLease(
            worker_id=worker_id,
            expires_at=datetime.fromtimestamp(expiration, timezone.utc).isoformat()
        )
        self.status = "RUNNING"
        self.updated_at = now.isoformat()
        return True

    def mark_completed(self) -> None:
        self.status = "COMPLETED"
        self.lease = None
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def mark_failed(self, error: str) -> None:
        self.status = "FAILED"
        self.lease = None
        self.error_history.append(error)
        self.updated_at = datetime.now(timezone.utc).isoformat()
