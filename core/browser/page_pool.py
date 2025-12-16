import asyncio
from typing import Optional, Any
from playwright.async_api import Browser, Page
from core.logger.logger_manager import LoggerManager

class PagePool:
    def __init__(self, browser: Browser, context: Any, max_size: int = 5) -> None:
        self.logger = LoggerManager.get_instance().get_logger(self.__class__.__name__)
        self.max_size = max_size
        self._browser = browser
        self._context = context
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=max_size)
        self._created_count = 0
        self._lock = asyncio.Lock()

    async def cleanup(self) -> None:
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except Exception as e:
                self.logger.error(f"Error closing page: {e}")

        self.logger.info("All pages closed")
        self._browser = None

    def acquire(self, is_resident: bool = False) -> "PageContext":
        return PageContext(self, is_resident)

    def get_created_count(self) -> int:
        return self._created_count

    def get_available_count(self) -> int:
        return self._queue.qsize()

    def get_max_size(self) -> int:
        return self.max_size

    async def safe_close_page(self, page: Page) -> None:
        if self._is_page_closed(page):
            return

        try:
            await page.close()
        except Exception as e:
            self.logger.error(f"Close page error: {e}")

    async def _acquire(self) -> Page:
        while True:
            try:
                while True:
                    page = self._queue.get_nowait()
                    if self._is_page_closed(page):
                        self.logger.info("Page is closed")
                        continue

                    return page
            except asyncio.QueueEmpty:
                pass
            except Exception as e:
                self.logger.error(f"Error getting page from queue: {e}")

            async with self._lock:
                if self._created_count < self.max_size:
                    page = await self._create_page()
                    if page:
                        return page

            try:
                page = await asyncio.wait_for(self._queue.get(), timeout=60)
                if self._is_page_closed(page):
                    self.logger.info("Page is closed")
                    continue

                return page
            except asyncio.TimeoutError:
                self.logger.error("Timeout waiting for page")
                raise TimeoutError("Timeout waiting for page")

    async def _release(self, page: Page) -> None:
        if self._is_page_closed(page):
            return

        try:
            self._queue.put_nowait(page)
            self.logger.info(f"Page released")
        except Exception as e:
            self.logger.warning(f"Error releasing page: {e}, closing page")
            await self.safe_close_page(page)


    async def _create_page(self) -> Optional[Page]:
        try:
            page = await self._context.new_page()
            self._created_count += 1
            page.on("close", lambda: self._on_page_closed(page))
            return page
        except Exception as e:
            self.logger.error(f"Error creating new page: {e}")
            return None

    def _on_page_closed(self, page: Page) -> None:
        self._created_count -= 1
        self.logger.info(f"Page closed: {page.url}")

    def _is_page_closed(self, page: Page) -> bool:
        return page is None or page.is_closed()

class PageContext:
    def __init__(self, pool: PagePool, is_resident: bool = False) -> None:
        self.pool = pool
        self.is_resident = is_resident
        self.page = None

    async def __aenter__(self) -> "PageContext":
        self.page = await self.pool._acquire()
        if self.is_resident:
            self.pool.logger.info("Page is resident")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.page is None:
            return

        if not self.is_resident:
            await self.pool._release(self.page)

        self.page = None

    def __getattr__(self, name) -> Any:
        if self.page:
            return getattr(self.page, name)
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
