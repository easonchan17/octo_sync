import asyncio
from typing import Optional, Any
from playwright.async_api import Browser, Page
from core.logger.logger_manager import LoggerManager

class PagePool:
    def __init__(self, browser: Browser, max_size: int = 5) -> None:
        self.logger = LoggerManager.get_instance().get_logger(self.__class__.__name__)
        self.max_size = max_size
        self._browser = browser
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=max_size)
        self._created_count = 0
        self.locked_pages = {}

    async def cleanup(self) -> None:
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except Exception as e:
                self.logger.error(f"Error closing page: {e}")

        self.logger.info("All pages closed")
        self.locked_pages.clear()
        self._browser = None

    def acquire(self) -> "PageContext":
        return PageContext(self)

    def get_created_count(self) -> int:
        return self._created_count

    def get_available_count(self) -> int:
        return self._queue.qsize()

    def get_max_size(self) -> int:
        return self.max_size

    def lock(self, locker: str, page: Page) -> None:
        if not locker or not page:
            return

        self.locked_pages[locker] = page
        self.logger.info(f"Page locked by {locker}")

    def is_locked(self, page: Page) -> bool:
        return page in self.locked_pages.values()

    async def safe_close_page(self, page: Page) -> None:
        if self._is_page_closed(page):
            return

        try:
            await page.close()
        except Exception as e:
            self.logger.error(f"Close page error: {e}")

    async def _acquire(self) -> Optional[Page]:
        try:
            page = None
            if not self._queue.empty():
                page = self._queue.get_nowait()

                if self._is_page_closed(page):
                    self.logger.info("Page already closed")
                    page = None
                elif self.is_locked(page):
                    self.logger.info("Page already locked")
                    self._queue.put_nowait(page)
                    page = None

            if page is None and self._created_count < self.max_size:
                page = await self._create_page()

            return page
        except Exception as e:
            self.logger.error(f"Error getting page from pool: {e}")
            return None

    async def _release(self, page: Page) -> None:
        if self._is_page_closed(page):
            return
        try:
            self._queue.put_nowait(page)
            self.logger.info("Page released")
        except Exception as e:
            self.logger.error(f"Error release page: {e}")
            await self.safe_close_page(page)


    async def _create_page(self) -> Optional[Page]:
        try:
            page = await self._browser.new_page()
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
    def __init__(self, pool: PagePool) -> None:
        self.pool = pool
        self.page = None

    async def __aenter__(self) -> "PageContext":
        self.page = await self.pool._acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.page:
            await self.pool._release(self.page)
            self.page = None

    def __getattr__(self, name) -> Any:
        if self.page:
            return getattr(self.page, name)
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
