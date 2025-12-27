import asyncio
import itertools
from typing import Optional, Any
from playwright.async_api import Browser, Page
from core.logger.logger_manager import LoggerManager

class PagePool:
    def __init__(self, browser: Browser, browser_context: Any, capacity: int) -> None:
        self.logger = LoggerManager.get_instance().get_logger(self.__class__.__name__)

        self._browser = browser
        self._context = browser_context

        self._capacity = capacity
        self._semaphore = asyncio.Semaphore(capacity)

        self.resident_pages = {}

    def get_capacity(self) -> int:
        return self._capacity

    def get_count(self) -> int:
        return self._capacity - self._semaphore._value

    def acquire(self, is_resident: bool = False, timeout: float = 0) -> "PageContext":
        return PageContext(self, is_resident, timeout)

    async def create_page(self, timeout: float) -> Optional[Page]:
        try:
            await asyncio.wait_for(self._semaphore.acquire(), timeout=timeout)
        except asyncio.TimeoutError:
            self.logger.error("Timeout while waiting to acquire a page from the pool")
            return None

        try:
            def _safe_release(*args) -> None:
                if self._semaphore._value < self._capacity:
                    self._semaphore.release()
                # self.logger.info("Released semaphore")

            page = await self._context.new_page()
            page.on("close", _safe_release)
            return page
        except Exception as e:
            self.logger.error(f"Error creating new page: {e}")
            _safe_release()
            return None

    async def close_page(self, page: Page) -> None:
        try:
            if page and not page.is_closed():
                await page.close()
        except Exception as e:
            self.logger.error(f"Close page error: {e}")

    def add_resident_page(self, page_id: int, page: Page) -> None:
        self.resident_pages[page_id] = page
        self.logger.info(f"Cached resident page with id: {page_id}")

    async def remove_resident_page(self, page_id: int) -> None:
        page = self.resident_pages.pop(page_id, None)
        await self.close_page(page)

class PageContext:
    _id_counter = itertools.count(1)

    def __init__(self, pool: PagePool, is_resident: bool, timeout: float) -> None:
        self.pool = pool
        self.is_resident = is_resident
        self.timeout = timeout
        self.page = None
        self.id = next(PageContext._id_counter)

    async def __aenter__(self) -> "PageContext":
        self.page = await self.pool.create_page(self.timeout)
        if self.page is None:
            raise asyncio.TimeoutError("Failed to create page from pool")

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.page is None:
            return

        if self.is_resident:
            self.pool.add_resident_page(self.id, self.page)
        else:
            await self.pool.close_page(self.page)

        self.page = None

    def __getattr__(self, name) -> Any:
        return getattr(self.page, name)
