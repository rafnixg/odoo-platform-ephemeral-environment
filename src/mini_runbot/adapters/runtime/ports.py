import socket

from mini_runbot.domain.errors import RuntimeOperationError


class SocketPortAllocator:
    def __init__(self, start: int, end: int) -> None:
        if not 1024 <= start <= end <= 65535:
            raise ValueError("Port range must be between 1024 and 65535")
        self.start = start
        self.end = end

    def allocate(self) -> int:
        for port in range(self.start, self.end + 1):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as candidate:
                try:
                    candidate.bind(("127.0.0.1", port))
                except OSError:
                    continue
                return port
        raise RuntimeOperationError("No preview ports are available in the configured range")
