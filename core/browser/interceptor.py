import time
import asyncio
from enum import Enum
from bs4 import BeautifulSoup
from queue import Queue, Empty
from core.utils.thread import Thread
from concurrent.futures import Future
from core.utils.singleton import Singleton
from playwright.async_api import WebSocket
from core.browser.page_pool import PagePool
from camoufox.async_api import AsyncCamoufox
from typing import Tuple, List, Optional, Any
from core.config.config_manager import ConfigManager
from core.utils.string_utils import is_valid_url
from core.browser.intercept_policy import (
    InterceptType,
    InterceptPolicy
)

class TaskType(Enum):
    OPEN_PAGE = 1
    CLOSE_PAGE = 2

class Interceptor(Thread, Singleton):
    def __init__(self) -> None:
        super().__init__()
        self.page_pool = None
        self.task_queue = Queue()

    def get_page_pool(self) -> Optional[PagePool]:
        return self.page_pool

    def submit_task(self, task_type: TaskType, **kwargs) -> Optional[Future]:
        future = Future()
        self.task_queue.put((task_type, future, kwargs))
        return future

    def _run(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._async_run())
        finally:
            loop.close()

    async def _async_run(self) -> None:
        config = ConfigManager.get_instance().get_config("browser")
        try:
            async with AsyncCamoufox(
                headless=config['headless'],
                channel=config['channel']
            ) as browser:
                context = await browser.new_context()
                self.page_pool = PagePool(browser, context, config['page_pool_size'])

                timeout = config.get('timeout', 15)
                page_delay = config.get('page_delay', 3)
                retry_count = config.get('retry_count', 3)

                while not self.stop_event.is_set():
                    await self._execute_task(timeout, page_delay, retry_count)

                await self.page_pool.cleanup()
        except Exception as e:
            self.logger.error(f"Error exit interceptor: {e}")
        finally:
            self.page_pool = None

    async def _execute_task(self, timeout: int, delay: int, retry_count: int) -> None:
        try:
            task_type, future, kwargs = self.task_queue.get_nowait()
        except Empty:
            await asyncio.sleep(0.1)
            return

        # OPEN_PAGE Task will be retried based on the following reasons:
        # 1. page pool is full (no available page in pool)
        # 2. acquired page is closed (page is not available)
        if task_type == TaskType.OPEN_PAGE:
            url = kwargs.get("url")
            intercept_policy = kwargs.get("intercept_policy")
            query_params = kwargs.get("query_params")
            site = kwargs.get("site")

            if not is_valid_url(url):
                self.logger.error(f"Invalid URL: {url}")
                return

            if not intercept_policy:
                self.logger.warning(f"No intercept policy for {url}")

            success = False
            collected_responses = None
            while not success and retry_count > 0 and not self.stop_event.is_set():
                success, collected_responses = await self._intercept(
                    url,
                    intercept_policy,
                    query_params,
                    site,
                    timeout
                )
                await asyncio.sleep(delay)
                retry_count -= 1

            if success:
                future.set_result((collected_responses, None))
            else:
                future.set_exception(Exception("Failed to intercept page"))
        elif task_type == TaskType.CLOSE_PAGE:
            page = kwargs.get("page")
            await self.page_pool.safe_close_page(page)
            future.set_result(True)

        self.task_queue.task_done()

    def _is_cloudflare_challenge(self, page_content: str) -> bool:
            soup = BeautifulSoup(page_content, 'html.parser')
            title = soup.title.string if soup.title else ""
            text = soup.get_text()

            if "Just a moment" in title:
                return True
            if "Verifying you are human" in text or "needs to review the security" in text:
                return True

            return False

    async def _wait_for_manual_verification(self, page_context, max_wait_time: int, check_interval=3) -> None:
        current_content = await page_context.content()
        if not self._is_cloudflare_challenge(current_content):
            return

        self.logger.info(f"Waiting for manual verification (max {max_wait_time}s)...")
        self.logger.info("Please complete the verification in the browser window")

        check_count = 0
        max_checks = (max_wait_time // check_interval) if max_wait_time > 0 else 300

        while check_count < max_checks:
            await asyncio.sleep(check_interval)
            check_count += 1

            try:
                current_content = await page_context.content()

                if not self._is_cloudflare_challenge(current_content):
                    self.logger.info("Verification completed successfully")
                    await page_context.wait_for_load_state("networkidle", timeout=max_wait_time*1000)
                    return

                success_element = page_context.locator("#challenge-success-text")
                if await success_element.count() != 1:
                    continue

                is_visible = await success_element.first.is_visible()
                if not is_visible:
                    continue

                self.logger.info("Verification success element detected, waiting for redirect...")
                await page_context.wait_for_url(
                    lambda url: not url.startswith("https://challenges.cloudflare.com"),
                    timeout=max_wait_time*1000
                )
                await page_context.wait_for_load_state("networkidle", timeout=max_wait_time*1000)
                self.logger.info("Verification completed and redirected")
                await asyncio.sleep(check_interval)
                return

            except Exception as e:
                self.logger.debug(f"Error checking verification status: {e}")

        self.logger.warning(f"Verification wait timeout after {max_wait_time}s, proceeding anyway")

    async def _intercept(
        self,
        url: str,
        intercept_policy: InterceptPolicy,
        query_params: dict[str, Any],
        site: Any,
        timeout: int
    ) -> Tuple[bool, Optional[List[Any]]]:
        collected_datas: List[Any] = []

        async def _http_request_handler(route, request) -> None:
            try:
                http_rule = intercept_policy.find_rule(
                    type=InterceptType.HTTP,
                    url=request.url
                )
                if http_rule and http_rule.sender:
                    overrides = await http_rule.sender.process(request, query_params)

                    if overrides and isinstance(overrides, dict):
                        await route.continue_(**overrides)
                        return
            except Exception as e:
                self.logger.error(f"Failed to send request: {e}")

            try:
                await route.continue_()
            except Exception as e:
                self.logger.error(f"Failed to continue request: {e}")

        async def _http_response_handler(response) -> None:
            if not response.ok:
                self.logger.warning(f"Skipping non-OK response: {response.url} {response.status}")
                return

            http_rule = intercept_policy.find_rule(
                type=InterceptType.HTTP,
                url=response.url
            )
            if not http_rule or not http_rule.receiver:
                return

            try:
                parsed_data = await http_rule.receiver.process(response)
                collected_datas.append(parsed_data)
            except Exception as e:
                self.logger.error(f"Failed to process response from {response.url} {response.request.method} {http_rule.receiver}: {e}", exc_info=True)

        async def _ws_connect_handler(ws: WebSocket):
            ws_rule = intercept_policy.find_rule(
                type=InterceptType.WS,
                url=ws.url
            )
            if not ws_rule or not ws_rule.receiver:
                return

            async def _framereceived_handler(frame):
                try:
                    await ws_rule.receiver.process(site, frame)
                except Exception as e:
                    self.logger.error(f"Failed to process ws frame from {ws.url}: {e}")

            async def _close_handler(code):
                self.logger.info(f"ws closed: {ws.url}, code {code}")

            async def _error_handler(error):
                self.logger.error(f"ws error: {ws.url} {error}")

            self.logger.info(f"ws opened: {ws.url}")

            ws.on("close", _close_handler)
            ws.on("error", _error_handler)
            ws.on("framereceived", _framereceived_handler)

        async def _page_content_handler(page_context) -> None:
            dom_rule = intercept_policy.find_rule(type=InterceptType.DOM)

            if dom_rule and dom_rule.receiver:
                parsed_data = await dom_rule.receiver.process(await page_context.content())
                collected_datas.append(parsed_data)

        async def _goto_page(page_context) -> None:
            self.logger.debug(f"Goto page {url}")
            start_time = time.time()

            await page_context.goto(url, wait_until='domcontentloaded', timeout=timeout*1000)
            try:
                await page_context.wait_for_load_state('networkidle', timeout=15000)
            except Exception:
                pass

            end_time = time.time()
            self.logger.info(f"page loaded ({end_time - start_time}s): {url}")

        is_resident = intercept_policy.has_rules(InterceptType.WS)
        async with self.page_pool.acquire(is_resident=is_resident) as page_context:
            if page_context.page is None:
                self.logger.error("Failed to get page (queue empty and max limit reached)")
                return False, None

            intercept_flag = False

            try:
                if intercept_policy.has_rules(InterceptType.HTTP):
                    if intercept_policy.has_senders(InterceptType.HTTP):
                        await page_context.route("**/*", _http_request_handler)

                    if intercept_policy.has_receivers(InterceptType.HTTP):
                        page_context.on("response", _http_response_handler)
                    self.logger.info(f"Register http request and response handler for page: {url}")

                if intercept_policy.has_rules(InterceptType.WS):
                    page_context.on("websocket", _ws_connect_handler)
                    collected_datas.append(page_context.page)
                    self.logger.info(f"Register ws handler for page: {url}")

                await _goto_page(page_context)
                await self._wait_for_manual_verification(page_context, timeout)

                if intercept_policy.has_rules(InterceptType.DOM):
                    await _page_content_handler(page_context)

                intercept_flag = True
            except Exception as e:
                self.logger.error(f"Error loading page {url}: {e}", exc_info=True)
            finally:
                if intercept_policy.has_rules(InterceptType.HTTP):
                    if intercept_policy.has_senders(InterceptType.HTTP):
                        try:
                            await page_context.unroute("**/*", _http_request_handler)
                        except Exception:
                            pass

                    if intercept_policy.has_receivers(InterceptType.HTTP):
                        try:
                            page_context.remove_listener("response", _http_response_handler)
                        except Exception:
                            pass

        return intercept_flag, collected_datas