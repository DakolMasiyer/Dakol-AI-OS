import os
import signal
import sys
import logging
from typing import Callable

logger = logging.getLogger(__name__)

class CloudRunServer:
    def __init__(self):
        self.is_ready = False
        self.is_shutting_down = False
        self._setup_signals()

    def _setup_signals(self):
        # Cloud Run sends SIGTERM when shutting down an instance
        signal.signal(signal.SIGTERM, self._handle_sigterm)
        signal.signal(signal.SIGINT, self._handle_sigterm)

    def _handle_sigterm(self, signum, frame):
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.is_shutting_down = True
        self.is_ready = False
        
        # In a real async loop, we'd signal tasks to drain
        # For synchronous execution, we just exit when safe
        sys.exit(0)

    def startup(self, init_fn: Callable[[], None]) -> None:
        """Runs initialization and marks server as ready."""
        try:
            init_fn()
            self.is_ready = True
            logger.info("Cloud Run container startup complete. Server is ready.")
        except Exception as e:
            logger.error(f"Startup failed: {e}")
            sys.exit(1)

    def health_check(self) -> dict[str, str]:
        """Liveness probe"""
        return {"status": "ok"}

    def readiness_check(self) -> tuple[dict[str, str], int]:
        """Readiness probe"""
        if self.is_ready and not self.is_shutting_down:
            return {"status": "ready"}, 200
        return {"status": "not_ready"}, 503
