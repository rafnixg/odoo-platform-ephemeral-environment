from threading import Event

from mini_runbot.application.scheduler import CleanupScheduler
from mini_runbot.domain.models import CleanupResult, PurgeResult


class RecordingManager:
    def __init__(self) -> None:
        self.called = Event()
        self.calls = 0

    def cleanup_expired(self) -> CleanupResult:
        self.calls += 1
        self.called.set()
        return CleanupResult(0, [], [])

    def purge_destroyed(self) -> PurgeResult:
        return PurgeResult(0, [], [])


def test_scheduler_runs_cleanup_and_stops() -> None:
    manager = RecordingManager()
    scheduler = CleanupScheduler(manager, interval_seconds=0.01)  # type: ignore[arg-type]

    scheduler.start()
    assert manager.called.wait(timeout=1)
    scheduler.stop()
    calls_after_stop = manager.calls
    assert not scheduler._thread or not scheduler._thread.is_alive()

    assert manager.calls == calls_after_stop
