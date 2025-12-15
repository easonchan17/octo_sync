import re
import time
import asyncio
from enum import Enum
from typing import Tuple
from queue import Queue, Empty
from bs4 import BeautifulSoup
from concurrent.futures import Future
from typing import List, Optional, Any
from playwright.async_api import WebSocket
from camoufox.async_api import AsyncCamoufox
from core.browser.page_pool import PagePool
from core.utils.thread import Thread
from core.utils.singleton import Singleton
from core.config.config_manager import ConfigManager
from core.utils.string_utils import normalize_url, is_valid_url
from core.browser.components.component_factory import ComponentFactory

class TaskType(Enum):
    OPEN_PAGE = 1
    CLOSE_PAGE = 2

class InterceptRule:
    def __init__(self, pattern: str, receiver: str, sender: Optional[str] = None, synchronizer: Optional[str] = None) -> None:
        self.pattern = pattern
        self.receiver = receiver
        self.sender = sender
        self.synchronizer = synchronizer


class InterceptRuleConverter:
    def __call__(self, rules: List[dict[str, Any]]) -> List[InterceptRule]:
        return [InterceptRule(rule.get("pattern"), rule.get("receiver"), rule.get("sender"), rule.get("synchronizer")) for rule in rules]


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
                self.page_pool = PagePool(browser, config['page_pool_size'])

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
            task_type, future, kwargs = self.task_queue.get(timeout=1)
        except Empty:
            await asyncio.sleep(delay)
            return

        # OPEN_PAGE Task will be retried based on the following reasons:
        # 1. page pool is full (no available page in pool)
        # 2. acquired page is closed (page is not available)
        if task_type == TaskType.OPEN_PAGE:

            url = kwargs.get("url")
            page_locker = kwargs.get("page_locker")
            http_rules = kwargs.get("http_rules")
            ws_rules = kwargs.get("ws_rules")
            html_handler = kwargs.get("html_handler")
            query_params = kwargs.get("query_params")
            site = kwargs.get("site")

            if not is_valid_url(url):
                self.logger.error(f"Invalid URL: {url}")
                return

            if not http_rules:
                self.logger.warning(f"No http intercept rules for {url}")

            if not ws_rules:
                self.logger.warning(f"No ws intercept rules for {url}")

            if not html_handler:
                self.logger.warning(f"No html handler for {url}")

            success = False
            collected_responses = None
            page_content = None
            while not success and retry_count > 0 and not self.stop_event.is_set():
                success, collected_responses, page_content = await self._intercept(
                    url,
                    page_locker,
                    http_rules,
                    ws_rules,
                    html_handler,
                    query_params,
                    site,
                    timeout
                )
                await asyncio.sleep(delay)
                retry_count -= 1

            if success:
                future.set_result((collected_responses, page_content))
        elif task_type == TaskType.CLOSE_PAGE:
            page = kwargs.get("page")
            await self.page_pool.safe_close_page(page)
            future.set_result(True)

        self.task_queue.task_done()

    def _find_matching_rule(self, url: str, intercept_rules: List[InterceptRule]) -> Optional[InterceptRule]:
        response_url = normalize_url(url)
        for rule in intercept_rules:
            if re.match(rule.pattern, response_url):
                return rule
        return None

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
        page_locker: str,
        http_rules: List[InterceptRule],
        ws_rules: List[InterceptRule],
        html_handler: str,
        query_params: dict[str, Any],
        site: Any,
        timeout: int
    ) -> Tuple[bool, Optional[List[Any]]]:
        page_content = None
        collected_datas: List[Any] = []

        async def _http_request_handler(route, request) -> None:
            try:
                http_rule = self._find_matching_rule(request.url, http_rules)

                if http_rule and http_rule.sender:
                    sender = await ComponentFactory.create_inst(http_rule.sender)
                    overrides = await sender.process(route, request, query_params)

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
            http_rule = self._find_matching_rule(response.url, http_rules)
            if not http_rule or not http_rule.receiver:
                return

            try:
                receiver = await ComponentFactory.create_inst(http_rule.receiver)
                parsed_data = await receiver.process(response)
                collected_datas.append(parsed_data)
            except Exception as e:
                self.logger.error(f"Failed to process response from {response.url} {response.request.method} {http_rule.receiver}: {e}", exc_info=True)

        async def _ws_connect_handler(ws: WebSocket):
            ws_rule = self._find_matching_rule(ws.url, ws_rules)
            if not ws_rule or not ws_rule.receiver:
                return

            async def _framereceived_handler(frame):
                try:
                    receiver = await ComponentFactory.create_inst(ws_rule.receiver)
                    await receiver.process(site, frame)
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

        async with self.page_pool.acquire() as page_context:
            if page_context.page is None:
                self.logger.error("Failed to get page (queue empty and max limit reached)")
                return False, None

            try:
                if http_rules:
                    await page_context.route("**/*", _http_request_handler)
                    page_context.on("response", _http_response_handler)
                    self.logger.info(f"Register http request and response handler for page: {url}")

                if ws_rules:
                    page_context.on("websocket", _ws_connect_handler)
                    self.logger.info(f"Register ws handler for page: {url}")

                self.logger.debug(f"Goto page {url}")
                start_time = time.time()
                await page_context.goto(url, wait_until='networkidle', timeout=timeout*1000)
                end_time = time.time()
                self.logger.info(f"page loaded ({end_time - start_time}s): {url}")

                await self._wait_for_manual_verification(page_context, timeout)

                if html_handler:
                    handler = await ComponentFactory.create_inst(html_handler)
                    page_content = await page_context.content()
                    parsed_data = await handler.process(page_content)
                    collected_datas.append(parsed_data)

                if page_locker:
                    self.page_pool.lock(page_locker, page_context.page)
                    collected_datas.append(page_context.page)

            except Exception as e:
                self.logger.error(f"Error loading page {url}: {e}", exc_info=True)
            finally:
                if http_rules:
                    await page_context.unroute("**/*", _http_request_handler)
                    page_context.remove_listener("response", _http_response_handler)

        return True, collected_datas, page_content