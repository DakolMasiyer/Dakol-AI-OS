from __future__ import annotations

import signal
import time

from app.core.logging import configure_logging, get_logger
from core.queue.worker import DistributedWorker
from runtime.environment import ensure_runtime_environment


logger = get_logger(__name__)


def main() -> None:
    configure_logging()
    manifest = ensure_runtime_environment(component="worker")
    worker = DistributedWorker(queue_name="default")

    shutting_down = {"value": False}

    def _stop(_signum, _frame) -> None:
        shutting_down["value"] = True
        logger.info("Worker shutdown requested", extra={"fingerprint": manifest["fingerprint"]})

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    logger.info(
        "Worker bootstrap complete",
        extra={
            "worker_id": worker.worker_id,
            "queue_name": worker.queue_name,
            "runtime_fingerprint": manifest["fingerprint"],
            "python_version": manifest["python_version"],
            "dependencies": manifest["dependencies"],
        },
    )

    while not shutting_down["value"]:
        time.sleep(5)


if __name__ == "__main__":
    main()
