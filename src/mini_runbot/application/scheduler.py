from __future__ import annotations

import logging
from threading import Event, Thread

from mini_runbot.application.build_manager import BuildManager

logger = logging.getLogger(__name__)


class CleanupScheduler:
    """Periodically destroys expired builds while one API process is running."""

    def __init__(self, manager: BuildManager, interval_seconds: float) -> None:
        if interval_seconds <= 0:
            raise ValueError("Cleanup interval must be positive")
        self.manager = manager
        self.interval_seconds = interval_seconds
        self._stop = Event()
        self._thread: Thread | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = Thread(
            target=self._run,
            name="mini-runbot-cleanup",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=max(1.0, self.interval_seconds + 1.0))

    def _run(self) -> None:
        while not self._stop.wait(self.interval_seconds):
            try:
                result = self.manager.cleanup_expired()
                if result.destroyed_ids or result.failed_ids:
                    logger.info(
                        "Expired build cleanup completed",
                        extra={
                            "destroyed_ids": result.destroyed_ids,
                            "failed_ids": result.failed_ids,
                        },
                    )
            except Exception:
                logger.exception("Scheduled expired build cleanup failed")
