import pytest

from mini_runbot.adapters.runtime.ports import SocketPortAllocator
from mini_runbot.domain.errors import RuntimeOperationError


class LeaseStore:
    def __init__(self) -> None:
        self.leases: dict[int, str] = {}

    def try_acquire_port(self, build_id: str, port: int) -> bool:
        if port in self.leases:
            return False
        self.leases[port] = build_id
        return True

    def release_port(self, build_id: str, port: int) -> None:
        if self.leases.get(port) == build_id:
            self.leases.pop(port)

    def reconcile_port_leases(self) -> list[int]:
        return []


def test_allocator_avoids_collisions_and_reuses_released_port() -> None:
    allocator = SocketPortAllocator(32101, 32102)

    first = allocator.allocate("build-one")
    second = allocator.allocate("build-two")
    allocator.release("build-one", first)
    reused = allocator.allocate("build-three")

    assert first != second
    assert reused == first


def test_allocator_skips_ports_reserved_by_persistence() -> None:
    allocator = SocketPortAllocator(32111, 32112)

    allocated = allocator.allocate("build-one", {32111})

    assert allocated == 32112


def test_stale_release_cannot_remove_new_build_lease() -> None:
    store = LeaseStore()
    allocator = SocketPortAllocator(32121, 32121, store)
    port = allocator.allocate("old-build")
    allocator.release("old-build", port)
    assert allocator.allocate("new-build") == port

    allocator.release("old-build", port)

    with pytest.raises(RuntimeOperationError, match="No preview ports"):
        allocator.allocate("third-build")
