from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Generator


@contextmanager
def ms_timer() -> Generator[list[int], None, None]:
    """Context manager that records elapsed milliseconds into a single-element list.

    Usage:
        with ms_timer() as elapsed:
            await do_something()
        print(elapsed[0])  # milliseconds
    """
    result: list[int] = [0]
    t0 = time.monotonic_ns()
    yield result
    result[0] = (time.monotonic_ns() - t0) // 1_000_000
