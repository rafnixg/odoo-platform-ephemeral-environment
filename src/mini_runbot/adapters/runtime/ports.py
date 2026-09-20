import socket
from threading import Lock

from mini_runbot.domain.errors import RuntimeOperationError
from mini_runbot.ports.repositories import PortLeaseStore


class SocketPortAllocator:
    def __init__(
        self, start: int, end: int, lease_store: PortLeaseStore | None = None
    ) -> None:
        if not 1024 <= start <= end <= 65535:
            raise ValueError("Port range must be between 1024 and 65535")
        self.start = start
        self.end = end
        self.lease_store = lease_store
        self._allocated: dict[int, str] = {}
        self._lock = Lock()

    def allocate(self, build_id: str, excluded: set[int] | None = None) -> int:
        excluded = excluded or set()
        with self._lock:
            for port in range(self.start, self.end + 1):
                if port in self._allocated or port in excluded:
                    continue
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as candidate:
                    try:
                        candidate.bind(("127.0.0.1", port))
                    except OSError:
                        continue
                    if self.lease_store and not self.lease_store.try_acquire_port(
                        build_id, port
                    ):
                        continue
                    self._allocated[port] = build_id
                    return port
        raise RuntimeOperationError("No preview ports are available in the configured range")

    def release(self, build_id: str, port: int) -> None:
        with self._lock:
            if self._allocated.get(port) == build_id:
                self._allocated.pop(port)
            if self.lease_store:
                self.lease_store.release_port(build_id, port)

    def reconcile(self) -> list[int]:
        if not self.lease_store:
            return []
        return self.lease_store.reconcile_port_leases()
