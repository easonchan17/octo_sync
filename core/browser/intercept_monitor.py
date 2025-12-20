import asyncio
from typing import Set
from core.browser.intercept_policy import InterceptType, InterceptPolicy

class InterceptMonitor:
    def __init__(self, policy: InterceptPolicy, intercept_type: InterceptType) -> None:
        self.policy = policy
        self._type = intercept_type

        patterns = self.policy.get_url_patterns(intercept_type)
        self._pending: Set[str] = set(patterns)
        self._done: asyncio.Event = asyncio.Event()

        if not self._pending:
            self._done.set()

    def is_completed(self) -> bool:
        return not self._pending

    def mark_completed(self, url: str) -> None:
        rule = self.policy.find_rule(type=self._type, url=url)

        if rule is None:
            raise ValueError(f"No rule found for URL: {url}")

        self._pending.discard(rule.pattern)
        if not self._pending:
            self._done.set()

    async def wait(self, timeout: float):
        if not self._pending:
            return

        try:
            await asyncio.wait_for(
                self._done.wait(),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            pending_patterns = ", ".join(self._pending)
            raise asyncio.TimeoutError(f"Timeout while waiting for intercept monitor: {pending_patterns}")

    def __repr__(self) -> str:
        return f"InterceptMonitor(pending_patterns={self._pending})"
