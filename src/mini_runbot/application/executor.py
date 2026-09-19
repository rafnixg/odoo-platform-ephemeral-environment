from __future__ import annotations

import logging
from concurrent.futures import Future, ThreadPoolExecutor
from threading import Lock

from mini_runbot.application.build_manager import BuildManager

logger = logging.getLogger(__name__)


class LocalBuildExecutor:
    """Bounded in-process executor for the PoC; it is not a durable queue."""

    def __init__(self, manager: BuildManager, max_workers: int = 2) -> None:
        self.manager = manager
        self.pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="mini-runbot")
        self._futures: dict[str, Future[object]] = {}
        self._lock = Lock()

    def submit(self, build_id: str) -> None:
        with self._lock:
            active = self._futures.get(build_id)
            if active is not None and not active.done():
                return
            future = self.pool.submit(self._execute, build_id)
            self._futures[build_id] = future

    def _execute(self, build_id: str) -> None:
        try:
            self.manager.execute(build_id)
        except Exception:
            logger.exception("Build execution failed", extra={"build_id": build_id})

    def is_active(self, build_id: str) -> bool:
        with self._lock:
            future = self._futures.get(build_id)
            return future is not None and not future.done()

    def shutdown(self, wait: bool = True) -> None:
        self.pool.shutdown(wait=wait, cancel_futures=False)
