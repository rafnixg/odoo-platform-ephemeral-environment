from threading import Event

from mini_runbot.application.executor import LocalBuildExecutor


class BlockingManager:
    def __init__(self) -> None:
        self.started = Event()
        self.release = Event()
        self.calls = 0

    def execute(self, build_id: str) -> None:
        self.calls += 1
        self.started.set()
        self.release.wait(timeout=2)


def test_executor_deduplicates_active_build() -> None:
    manager = BlockingManager()
    executor = LocalBuildExecutor(manager, max_workers=1)  # type: ignore[arg-type]
    try:
        executor.submit("build-one")
        assert manager.started.wait(timeout=2)
        executor.submit("build-one")
        assert executor.is_active("build-one")
        manager.release.set()
        executor.shutdown()
        assert manager.calls == 1
    finally:
        manager.release.set()
