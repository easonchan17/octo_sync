import asyncio
from typing import List, Set

class SignalLatch:
    def __init__(self) -> None:
        self._done = asyncio.Event()

    def mark_completed(self) -> None:
        self._done.set()

    async def wait(self, timeout: float) -> None:
        try:
            await asyncio.wait_for(self._done.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            raise asyncio.TimeoutError("Timeout while waiting for event")

class PatternLatch:
    def __init__(self, patterns: List[str]) -> None:
        self._pending: Set[str] = set(patterns)
        self._done: asyncio.Event = asyncio.Event()

        if not self._pending:
            self._done.set()

    def mark_completed(self, pattern: str) -> None:
        self._pending.discard(pattern)
        if not self._pending:
            self._done.set()

    async def wait(self, timeout: float) -> None:
        if not self._pending:
            return

        try:
            await asyncio.wait_for(self._done.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            pending_patterns = ", ".join(self._pending)
            raise asyncio.TimeoutError(f"Timeout while waiting for intercept monitor: {pending_patterns}")
