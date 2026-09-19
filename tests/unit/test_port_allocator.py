from mini_runbot.adapters.runtime.ports import SocketPortAllocator


def test_allocator_avoids_collisions_and_reuses_released_port() -> None:
    allocator = SocketPortAllocator(32101, 32102)

    first = allocator.allocate()
    second = allocator.allocate()
    allocator.release(first)
    reused = allocator.allocate()

    assert first != second
    assert reused == first
