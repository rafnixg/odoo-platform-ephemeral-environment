import socket
from threading import Lock

from mini_runbot.domain.errors import RuntimeOperationError


class SocketPortAllocator:
    def __init__(self, start: int, end: int) -> None:
        if not 1024 <= start <= end <= 65535:
            raise ValueError("Port range must be between 1024 and 65535")
        self.start = start
        self.end = end
        self._allocated: set[int] = set()
        self._lock = Lock()

    def allocate(self) -> int:
        with self._lock:
            for port in range(self.start, self.end + 1):
                if port in self._allocated:
                    continue
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as candidate:
                    try:
                        candidate.bind(("127.0.0.1", port))
                    except OSError:
                        continue
                    self._allocated.add(port)
                    return port
        raise RuntimeOperationError("No preview ports are available in the configured range")

    def release(self, port: int) -> None:
        with self._lock:
            self._allocated.discard(port)
