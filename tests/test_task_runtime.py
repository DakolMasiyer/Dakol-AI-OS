import json
import tempfile
import unittest
from pathlib import Path

from runtime.tasks import (
    VALID_STATUSES,
    get_task,
    list_tasks,
    run_task,
    submit_task,
    update_task,
)


class TaskRuntimeTests(unittest.TestCase):
    def test_submit_task_persists_queued_task_with_id(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tasks_path = Path(temp_dir) / "tasks.json"

            task = submit_task(
                "sync metadata",
                metadata={"priority": "high"},
                tasks_path=str(tasks_path),
            )
            saved = json.loads(tasks_path.read_text())

            self.assertEqual(len(saved), 1)
            self.assertEqual(task["task_id"], saved[0]["task_id"])
            self.assertTrue(task["task_id"])
            self.assertEqual(task["status"], "queued")
            self.assertEqual(task["task"], "sync metadata")
            self.assertEqual(task["metadata"], {"priority": "high"})
            self.assertIsNone(task["result"])
            self.assertIsNone(task["error"])

    def test_list_get_and_update_task(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tasks_path = str(Path(temp_dir) / "tasks.json")
            first = submit_task("first", tasks_path=tasks_path)
            second = submit_task("second", tasks_path=tasks_path)

            updated = update_task(
                second["task_id"],
                status="cancelled",
                metadata={"reason": "duplicate"},
                tasks_path=tasks_path,
            )

            self.assertEqual(updated["status"], "cancelled")
            self.assertEqual(updated["metadata"], {"reason": "duplicate"})
            self.assertEqual(get_task(first["task_id"], tasks_path=tasks_path), first)
            self.assertEqual(list_tasks(status="queued", tasks_path=tasks_path), [first])
            self.assertEqual(list_tasks(status="cancelled", tasks_path=tasks_path), [updated])

    def test_status_validation(self):
        self.assertEqual(
            VALID_STATUSES,
            {"queued", "running", "completed", "failed", "cancelled"},
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            tasks_path = str(Path(temp_dir) / "tasks.json")
            task = submit_task("bad status", tasks_path=tasks_path)

            with self.assertRaises(ValueError):
                update_task(task["task_id"], status="waiting", tasks_path=tasks_path)

            with self.assertRaises(ValueError):
                list_tasks(status="waiting", tasks_path=tasks_path)

    def test_run_task_persists_result(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tasks_path = str(Path(temp_dir) / "tasks.json")
            task = submit_task("add numbers", tasks_path=tasks_path)

            completed = run_task(
                task["task_id"],
                lambda left, right: {"sum": left + right},
                2,
                3,
                tasks_path=tasks_path,
            )
            saved = get_task(task["task_id"], tasks_path=tasks_path)

            self.assertEqual(completed["status"], "completed")
            self.assertEqual(completed["result"], {"sum": 5})
            self.assertIsNone(completed["error"])
            self.assertEqual(saved, completed)

    def test_run_task_persists_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tasks_path = str(Path(temp_dir) / "tasks.json")
            task = submit_task("explode", tasks_path=tasks_path)

            def fail():
                raise RuntimeError("boom")

            failed = run_task(task["task_id"], fail, tasks_path=tasks_path)

            self.assertEqual(failed["status"], "failed")
            self.assertEqual(failed["error"], {"type": "RuntimeError", "message": "boom"})
            self.assertIsNone(failed["result"])
            self.assertEqual(get_task(task["task_id"], tasks_path=tasks_path), failed)

    def test_cancelled_task_is_not_run(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tasks_path = str(Path(temp_dir) / "tasks.json")
            task = submit_task("skip me", tasks_path=tasks_path)
            cancelled = update_task(
                task["task_id"],
                status="cancelled",
                tasks_path=tasks_path,
            )

            result = run_task(
                task["task_id"],
                lambda: "should not run",
                tasks_path=tasks_path,
            )

            self.assertEqual(result, cancelled)
            self.assertEqual(get_task(task["task_id"], tasks_path=tasks_path), cancelled)


if __name__ == "__main__":
    unittest.main()
