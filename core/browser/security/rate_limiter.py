import time
import random
import asyncio
from contextlib import suppress
from urllib.parse import urlparse
from typing import Optional, Any
from core.logger.logger_manager import LoggerManager

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
        429: 2,
        502: 1,
        503: 5,
        504: 2
    }

    MAX_PENALTY_FACTOR = 120

    def __init__(self, base_interval: float = 60.0) -> None:
        self.logger = LoggerManager.get_instance().get_logger(self.__class__.__name__)
        self.last_request: dict[str, float] = {}
        self.backoff_until: dict[str, float] = {}
        self.host_penalties: dict[str, int] = {}
        self.base_interval = base_interval

    async def throttle(self, url: str) -> None:
        hostname = urlparse(url).hostname
        if not hostname:
            raise ValueError(f"Invalid URL: {url}")

        backoff_time = self.backoff_until.get(hostname, 0)
        last_time = self.last_request.get(hostname, 0)

        delay = self.base_interval * random.uniform(1.0, 1.5)
        target_time = max(backoff_time, last_time + delay)

        current_time = time.time()
        if target_time > current_time:
            wait_time = target_time - current_time
            self.logger.debug(f"Throttling request to {hostname}, waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)

        self.last_request[hostname] = time.time()

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

        penalty = self.host_penalties.get(hostname, 0) + self.STATUS_PENALTIES(status, 1)
        self.host_penalties[hostname] = penalty

        wait_time = min(self.base_interval * (2 ** (penalty - 1)), self.base_interval * self.MAX_PENALTY_FACTOR)
        self.backoff_until[hostname] = time.time() + wait_time

        self.logger.warning(f"Rate limit detected ({status}) for {hostname}, backing off for {wait_time}s")

    def reset_backoff(self, url: str) -> None:
        hostname = urlparse(url).hostname
        if not hostname:
            raise ValueError(f"Invalid URL: {url}")

        self.host_penalties.pop(hostname, None)
        self.backoff_until.pop(hostname, None)
