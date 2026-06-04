from __future__ import annotations

from runtime.task_store import TaskStore


class TaskRunner:
    def __init__(self, store: TaskStore | None = None):
        self.store = store or TaskStore()

    def run(self, task_id: str, executor) -> dict:
        current = self.store.get(task_id)
        if current is None:
            raise ValueError(f"No task found for task_id: {task_id}")
        if current.get("status") == "cancelled":
            return current

        task = self.store.update(task_id, status="running", error=None)
        try:
            result = executor(task)
            return self.store.update(task_id, status="completed", result=result, error=None)
        except Exception as exc:
            return self.store.update(task_id, status="failed", error=str(exc), result=None)
