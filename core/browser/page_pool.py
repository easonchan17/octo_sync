import asyncio
from typing import Optional, Any
from playwright.async_api import Browser, Page
from core.logger.logger_manager import LoggerManager

class PagePool:
    def __init__(
        self,
        browser: Browser,
        context: Any,
        max_size: int,
        enable_recycling: bool = False
    ) -> None:
        self.logger = LoggerManager.get_instance().get_logger(self.__class__.__name__)

        self._browser = browser
        self._context = context
        self.max_size = max_size

        self._queue: asyncio.Queue = asyncio.Queue() if enable_recycling else None
        self.enable_recycling = enable_recycling

        self._created_count = 0
        self._slot_available_condition = asyncio.Condition()

    async def cleanup(self) -> None:
        self.logger.info("Cleaning up page pool")

        if self._queue:
            while not self._queue.empty():
                try:
                    page = self._queue.get_nowait()
                    await self.safe_close_page(page)
                except Exception as e:
                    self

        self.logger.info("All pages closed")

    def acquire(self, is_resident: bool = False, timeout: float = 0) -> "PageContext":
        return PageContext(self, is_resident, timeout)

    def get_created_count(self) -> int:
        return self._created_count

    def get_available_count(self) -> int:
        return self.max_size - self._created_count

    def get_max_size(self) -> int:
        return self.max_size

    async def safe_close_page(self, page: Page) -> None:
        if self._is_page_closed(page):
            return

        try:
            await page.close()
        except Exception as e:
            self.logger.error(f"Close page error: {e}")

    async def _acquire(self, timeout: float) -> Optional[Page]:
        async with self._slot_available_condition:
            async def get() -> Optional[Page]:
                page = self._get_idle_page()
                if page:
                    return page

                page = await self._try_create_page()
                if page:
                    return page

                return None

            page = await get()
            if page:
                return page

            try:
                await asyncio.wait_for(self._slot_available_condition.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                pass

            return await get()



    async def _release(self, page: Page) -> None:
        if self._is_page_closed(page):
            return

        if not self.enable_recycling:
            await self.safe_close_page(page)
            return

        try:
            self._queue.put_nowait(page)
            async with self._slot_available_condition:
                self._slot_available_condition.notify()
            self.logger.info(f"Page released")
        except Exception as e:
            self.logger.warning(f"Error releasing page: {e}, closing page")
            await self.safe_close_page(page)


    def _get_idle_page(self) -> Optional[Page]:
        if not self.enable_recycling:
            return None

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

        return None

    async def _try_create_page(self) -> Optional[Page]:
        if self._created_count >= self.max_size:
            return None

        return await self._create_page()

    async def _create_page(self) -> Optional[Page]:
        try:
            page = await self._context.new_page()
            page.on("close", lambda p: asyncio.create_task(self._on_page_closed(p)))
            self._created_count += 1
            return page
        except Exception as e:
            self.logger.error(f"Error creating new page: {e}")
            return None

    async def _on_page_closed(self, page: Page) -> None:
        async with self._slot_available_condition:
            self._created_count -= 1
            self._slot_available_condition.notify()
            self.logger.info(f"Page closed: {page.url}")

    def _is_page_closed(self, page: Page) -> bool:
        return page is None or page.is_closed()

class PageContext:
    def __init__(self, pool: PagePool, is_resident: bool, timeout: float) -> None:
        self.pool = pool
        self.is_resident = is_resident
        self.timeout = timeout
        self.page = None

    async def __aenter__(self) -> "PageContext":
        self.page = await self.pool._acquire(self.timeout)
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
