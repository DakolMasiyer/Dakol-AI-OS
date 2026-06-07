import json
import os
from datetime import datetime
from uuid import uuid4

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
TASKS_FILE = os.path.join(BASE_DIR, "memory", "tasks.json")
VALID_STATUSES = {"queued", "running", "completed", "failed", "cancelled"}

_MISSING = object()


def _now():
    return datetime.now().isoformat()


def _validate_status(status):
    if status not in VALID_STATUSES:
        valid = ", ".join(sorted(VALID_STATUSES))
        raise ValueError(f"status must be one of: {valid}")


def load_tasks(tasks_path=None):
    path = tasks_path or TASKS_FILE
    try:
        with open(path, "r") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_tasks(tasks, tasks_path=None):
    path = tasks_path or TASKS_FILE
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w") as f:
        json.dump(tasks, f, indent=2)


def submit_task(task, metadata=None, tasks_path=None):
    tasks = load_tasks(tasks_path)
    timestamp = _now()
    meta = dict(metadata or {})

    try:
        from app.core.tracing import get_request_id, get_workflow_id
        req_id = get_request_id()
        if req_id:
            meta["request_id"] = req_id
        work_id = get_workflow_id()
        if work_id:
            meta["workflow_id"] = work_id
    except ImportError:
        pass

    entry = {
        "task_id": str(uuid4()),
        "status": "queued",
        "task": task,
        "metadata": meta,
        "result": None,
        "error": None,
        "created_at": timestamp,
        "updated_at": timestamp,
    }

    tasks.append(entry)
    save_tasks(tasks, tasks_path)
    return entry



def list_tasks(status=None, tasks_path=None):
    if status is not None:
        _validate_status(status)

    tasks = load_tasks(tasks_path)
    if status is None:
        return tasks
    return [task for task in tasks if task.get("status") == status]


def get_task(task_id, tasks_path=None):
    for task in load_tasks(tasks_path):
        if task.get("task_id") == task_id:
            return task
    return None


def update_task(
    task_id,
    status=None,
    result=_MISSING,
    error=_MISSING,
    metadata=_MISSING,
    tasks_path=None,
):
    if status is not None:
        _validate_status(status)

    tasks = load_tasks(tasks_path)
    for task in tasks:
        if task.get("task_id") != task_id:
            continue

        if status is not None:
            task["status"] = status
        if result is not _MISSING:
            task["result"] = result
        if error is not _MISSING:
            task["error"] = error
        if metadata is not _MISSING:
            task["metadata"] = metadata or {}

        task["updated_at"] = _now()
        save_tasks(tasks, tasks_path)
        return task

    raise ValueError(f"No task found for task_id: {task_id}")


def run_task(task_id, worker, *args, tasks_path=None, **kwargs):
    task = get_task(task_id, tasks_path)
    if task is None:
        raise ValueError(f"No task found for task_id: {task_id}")
    if task.get("status") == "cancelled":
        return task

    update_task(task_id, status="running", error=None, tasks_path=tasks_path)
    try:
        result = worker(*args, **kwargs)
    except Exception as exc:
        return update_task(
            task_id,
            status="failed",
            error={
                "type": exc.__class__.__name__,
                "message": str(exc),
            },
            tasks_path=tasks_path,
        )

    return update_task(
        task_id,
        status="completed",
        result=result,
        error=None,
        tasks_path=tasks_path,
    )
