import time, random, asyncio
from typing import Any
from urllib.parse import urlparse
from core.logger.logger_manager import get_logger_manager

class RateLimiter:
    PREVIEW_LENGTH = 2000

    RATE_LIMIT_LABELS = [
        "too many requests",
        "rate limit",
        "quota exceeded",
        "wait a moment",
        "retry after"
    ]

    STATUS_PENALTIES = {
        429: 3,
        502: 1,
        503: 1,
        504: 1,
        -1: 1,
        -2: 1
    }

    def __init__(self, base_interval: float, max_backoff: float) -> None:
        self.logger = get_logger_manager().get_logger(self.__class__.__name__)
        self.last_request: dict[str, float] = {}
        self.backoff_until: dict[str, float] = {}
        self.host_penalties: dict[str, int] = {}
        self.base_interval = base_interval
        self.max_backoff = max_backoff

    async def throttle(self, url: str) -> None:
        hostname = urlparse(url).hostname
        if not hostname:
            raise ValueError(f"Invalid URL: {url}")

        backoff_time = self.backoff_until.get(hostname, 0)
        last_time = self.last_request.get(hostname, 0)

        delay = self.base_interval * random.uniform(1.0, 1.5)
        target_time = max(backoff_time, last_time + delay)

        wait_time = max(target_time - time.monotonic(), random.uniform(1.0, 3.0))
        self.logger.debug(f"Throttling request to {hostname}, waiting {wait_time:.2f}s")
        await asyncio.sleep(wait_time)

        self.last_request[hostname] = time.monotonic()

    async def is_rate_limited(self, response: Any) -> bool:
        if response.status in self.STATUS_PENALTIES:
            return True

        try:
            content = await response.text()
            content_preview = content[:self.PREVIEW_LENGTH].lower()

            if any(key in content_preview for key in self.RATE_LIMIT_LABELS):
                return True

        except Exception:
            pass

        return False

    def activate_backoff(self, url: str, status: int) -> None:
        hostname = urlparse(url).hostname
        if not hostname:
            raise ValueError(f"Invalid URL: {url}")

        penalty = self.host_penalties.get(hostname, 0) + self.STATUS_PENALTIES.get(status, 1)
        self.host_penalties[hostname] = penalty

        wait_time = min(self.base_interval * (2 ** (penalty - 1)), self.max_backoff)
        self.backoff_until[hostname] = time.monotonic() + wait_time

        self.logger.warning(f"Rate limit detected ({status}) for {hostname}, backing off for {wait_time}s")

    def reset_backoff(self, url: str) -> None:
        hostname = urlparse(url).hostname
        if not hostname:
            raise ValueError(f"Invalid URL: {url}")

        self.host_penalties.pop(hostname, None)
        self.backoff_until.pop(hostname, None)
