import time
import asyncio
from contextlib import suppress
from urllib.parse import urlparse
from typing import Optional, Any, Tuple
from core.logger.logger_manager import LoggerManager

class RateLimiter:
    PREVIEW_LENGTH = 1000
    BASE_DELAY = 20.0

    RATE_LIMIT_LABELS = [
        "too many requests",
        "rate limit",
        "quota exceeded",
        "wait a moment",
        "retry after"
    ]

    def __init__(self) -> None:
        self.logger = LoggerManager.get_instance().get_logger(self.__class__.__name__)
        self.last_request: dict[str, float] = {}
        self.backoff_until: dict[str, float] = {}
        self.consecutive_errors: dict[str, int] = {}

    async def throttle(self, url: str, delay: Optional[float] = None) -> None:
        hostname = urlparse(url).hostname
        if not hostname:
            raise ValueError(f"Invalid URL: {url}")

        backoff_time = self.backoff_until.get(hostname, 0)
        last_time = self.last_request.get(hostname, 0)
        target_time = max(backoff_time, last_time + (delay or 3.0))

        current_time = time.time()
        if target_time > current_time:
            wait_time = target_time - current_time
            self.logger.info(f"Throttling request to {hostname}, waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)

        self.last_request[hostname] = time.time()

    async def is_rate_limited(self, response: Optional[Any], page_context: Any) -> Tuple[bool, Optional[float]]:
        if response and response.status in [429, 503]:
            with suppress(Exception):
                if raw_value := response.headers.get('retry-after'):
                    return True, float(raw_value)

            return True, None

        with suppress(Exception):
            body_preview = await page_context.eval_on_selector(
                "body",
                f"el => el.innerText.substring(0, {self.PREVIEW_LENGTH})"
            )
            if not body_preview:
                return False, None

            content = body_preview.lower()
            if any(key in content for key in self.RATE_LIMIT_LABELS):
                return True, None

        return False, None

    def activate_backoff(self, url: str, delay: Optional[float] = None) -> None:
        hostname = urlparse(url).hostname
        if not hostname:
            raise ValueError(f"Invalid URL: {url}")

        count = self.consecutive_errors.get(hostname, 0) + 1
        wait_time = min(self.BASE_DELAY * (2 ** (count - 1)), self.BASE_DELAY * 10) if delay is None else delay

        self.consecutive_errors[hostname] = count
        self.backoff_until[hostname] = time.time() + wait_time
        self.logger.warning(f"Rate limit detected (429) for {hostname}, backing off for {wait_time}s")

    def reset_backoff(self, url: str) -> None:
        hostname = urlparse(url).hostname
        if not hostname:
            raise ValueError(f"Invalid URL: {url}")

        self.consecutive_errors.pop(hostname, None)
        self.backoff_until.pop(hostname, None)
