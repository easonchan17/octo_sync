import asyncio
import itertools
from typing import Optional, Any, Tuple
from core.logger.logger_manager import LoggerManager
from playwright.async_api import Browser, Page, BrowserContext

class PagePool:
    def __init__(self, browser: Browser, capacity: int) -> None:
        self.logger = LoggerManager.get_instance().get_logger(self.__class__.__name__)

        self._browser = browser
        self._capacity = capacity
        self._semaphore = asyncio.BoundedSemaphore(capacity)

    def acquire(self, timeout: float = 0) -> "PageContext":
        return PageContext(self, timeout)

    async def create(self, timeout: float) -> Tuple[Optional[BrowserContext], Optional[Page]]:
        try:
            await asyncio.wait_for(self._semaphore.acquire(), timeout=timeout)
        except asyncio.TimeoutError:
            self.logger.error("Timeout while waiting to acquire a page from the pool")
            raise

        def _safe_release(*args) -> None:
            try:
                self._semaphore.release()
                self.logger.info(f"Released semaphore successfully.")
            except Exception as e:
                self.logger.error(f"Error releasing semaphore: {e}")

        context = None

        try:
            context = await self._browser.new_context()
            page = await context.new_page()
            page.on("close", _safe_release)

            return context, page
        except Exception as e:
            self.logger.error(f"Error creating new page: {e}")
            await self.close(context)
            _safe_release()
            raise

    async def close(self, context: BrowserContext) -> None:
        if context is None:
            return

        try:
            await context.close()
        except Exception as e:
            self.logger.error(f"Error closing context: {e}", exc_info=True)

class PageContext:
    _id_counter = itertools.count(1)

    def __init__(self, pool: PagePool, timeout: float) -> None:
        self.id = next(PageContext._id_counter)
        self.pool = pool
        self.timeout = timeout
        self.context = None
        self.page = None
        self.detached = False

    async def __aenter__(self) -> "PageContext":
        self.context, self.page = await self.pool.create(self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.detached:
            return

        await self.pool.close(self.context)
        self.context = None
        self.page = None

    def __getattr__(self, name) -> Any:
        return getattr(self.page, name)

    def detach(self) -> None:
        self.detached = True