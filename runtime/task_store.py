from __future__ import annotations

import json
import os
from datetime import datetime
from uuid import uuid4


BASE_DIR = os.path.dirname(os.path.dirname(__file__))
TASK_STORE_FILE = os.path.join(BASE_DIR, "memory", "tasks.json")
TASK_STATUSES = {"queued", "running", "completed", "failed", "cancelled"}


class TaskStore:
    def __init__(self, path: str = TASK_STORE_FILE):
        self.path = path

    def submit(self, objective: str, plan=None, planner_used=None) -> dict:
        task = {
            "task_id": str(uuid4()),
            "objective": objective,
            "status": "queued",
            "created_at": _now(),
            "updated_at": _now(),
            "planner_used": planner_used,
            "plan": plan,
            "result": None,
            "error": None,
        }
        tasks = self.load()
        tasks.append(task)
        self.save(tasks)
        return task

    def load(self) -> list[dict]:
        try:
            with open(self.path, "r") as file:
                data = json.load(file)
                return data if isinstance(data, list) else []
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def save(self, tasks: list[dict]) -> None:
        parent = os.path.dirname(self.path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(self.path, "w") as file:
            json.dump(tasks, file, indent=2)

    def list(self, status: str | None = None) -> list[dict]:
        if status is not None and status not in TASK_STATUSES:
            raise ValueError(f"invalid task status: {status}")
        tasks = self.load()
        if status is None:
            return tasks
        return [task for task in tasks if task.get("status") == status]

    def get(self, task_id: str) -> dict | None:
        for task in self.load():
            if task.get("task_id") == task_id:
                return task
        return None

    def update(self, task_id: str, **changes) -> dict:
        tasks = self.load()
        for task in tasks:
            if task.get("task_id") == task_id:
                status = changes.get("status")
                if status and status not in TASK_STATUSES:
                    raise ValueError(f"invalid task status: {status}")
                task.update(changes)
                task["updated_at"] = _now()
                self.save(tasks)
                return task
        raise ValueError(f"No task found for task_id: {task_id}")


def _now() -> str:
    return datetime.now().isoformat()
