import json
from pathlib import Path
from typing import Any, Callable, Optional

class DuplicateGradingError(Exception):
    pass

class GradingQueueManager:
    def __init__(self, root_dir: Optional[Path] = None):
        self.root_dir = root_dir or Path(__file__).resolve().parents[2]
        self.grading_dir = self.root_dir / "logs" / "grading"
        self.grading_dir.mkdir(parents=True, exist_ok=True)
        self.processed_jobs_file = self.grading_dir / "processed_jobs.json"

    def _load_processed(self) -> set[str]:
        if not self.processed_jobs_file.exists():
            return set()
        data = json.loads(self.processed_jobs_file.read_text())
        return set(data)

    def _save_processed(self, processed: set[str]) -> None:
        self.processed_jobs_file.write_text(json.dumps(list(processed), sort_keys=True))

    def dispatch(self, job_id: str, grading_func: Callable[[], Any]) -> Any:
        """
        Idempotent dispatcher. If job_id has already been successfully processed,
        it raises DuplicateGradingError (or returns cached if we chose to).
        For strict deduplication, we raise error or simply return a "Skipped" response.
        """
        processed = self._load_processed()
        if job_id in processed:
            raise DuplicateGradingError(f"Job {job_id} has already been graded.")
        
        # Execute the grading synchronously (for replayability guarantees)
        # In a real distributed system, we'd wrap this in Celery/RQ, but the deduplication logic holds.
        try:
            result = grading_func()
            
            # Atomic-like commit
            processed.add(job_id)
            self._save_processed(processed)
            
            return result
        except Exception as e:
            # Failed grading recoverable (not marked as processed)
            raise e
