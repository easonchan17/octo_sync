import asyncio
import itertools
from typing import Optional, Any
from core.logger.logger_manager import LoggerManager
from playwright.async_api import Page, BrowserContext

class PagePool:
    def __init__(self, context: BrowserContext, capacity: int) -> None:
        self.logger = LoggerManager.get_instance().get_logger(self.__class__.__name__)
        self._context = context
        self._capacity = capacity
        self._semaphore = asyncio.BoundedSemaphore(capacity)

    def acquire(self, timeout: float = 0) -> "PageContext":
        return PageContext(self, timeout)

    def _safe_release(self, *args) -> None:
        try:
            self._semaphore.release()
            self.logger.info(f"Released semaphore successfully.")
        except Exception as e:
            self.logger.error(f"Error releasing semaphore: {e}")

    async def create(self, timeout: float) -> Optional[Page]:
        try:
            await asyncio.wait_for(self._semaphore.acquire(), timeout=timeout)
        except asyncio.TimeoutError:
            self.logger.error("Timeout while waiting to acquire a page from the pool")
            raise

        page = None
        try:
            page = await self._context.new_page()
            page.on("close", self._safe_release)
            return page
        except Exception as e:
            self.logger.error(f"Error creating new page: {e}")
            await self.close(page)
            self._safe_release()
            raise

    async def close(self, page: Page) -> None:
        if page is None or page.is_closed():
            return

        try:
            await page.close()
        except Exception as e:
            self.logger.error(f"Error closing page: {e}", exc_info=True)

class PageContext:
    _id_counter = itertools.count(1)

    def __init__(self, pool: PagePool, timeout: float) -> None:
        self.id = next(PageContext._id_counter)
        self.pool = pool
        self.timeout = timeout
        self.page = None
        self.detached = False

    async def __aenter__(self) -> "PageContext":
        self.page = await self.pool.create(self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.detached:
            return

        await self.pool.close(self.page)
        self.page = None

    def __getattr__(self, name: str) -> Any:
        if self.page is None:
            raise AttributeError(f"PageContext has no attribute '{name}' (page not initialized)")
        return getattr(self.page, name)

    def detach(self) -> None:
        self.detached = True