import time
import janus
import asyncio
from enum import Enum
from core.utils.thread import Thread
from concurrent.futures import Future
from core.utils.singleton import Singleton
from playwright.async_api import WebSocket
from core.browser.page_pool import PagePool
from camoufox.async_api import AsyncCamoufox
from typing import Tuple, List, Optional, Any
from core.utils.string_utils import is_valid_url
from core.config.config_manager import ConfigManager
from core.browser.cloudflare_handler import CloudflareHandler
from core.browser.intercept_policy import InterceptType, InterceptPolicy


class TaskType(Enum):
    OPEN_PAGE = 1
    CLOSE_PAGE = 2


class Interceptor(Thread, Singleton):
    def __init__(self) -> None:
        super().__init__()
        self.page_pool = None
        self.task_queue: Optional[janus.Queue] = None
        self.cloudflare_handler = CloudflareHandler()

    def get_page_pool(self) -> Optional[PagePool]:
        return self.page_pool

    def submit_task(self, task_type: TaskType, **kwargs) -> Optional[Future]:
        if self.task_queue is None:
            self.logger.error("Task queue is not initialized")
            return None

        future = Future()
        self.task_queue.sync_q.put((task_type, future, kwargs))
        return future

    def stop(self) -> None:
        if self.task_queue is not None:
            self.task_queue.sync_q.put(None)

        super().stop()

    def _run(self) -> None:
        loop = asyncio.new_event_loop()

        asyncio.set_event_loop(loop)
        self.task_queue = janus.Queue()

        try:
            loop.run_until_complete(self._async_run())
        except Exception as e:
            self.logger.error(f"Error in Interceptor thread: {e}")
        finally:
            loop.close()

    async def _async_run(self) -> None:
        config = ConfigManager.get_instance().get_config("browser")
        headless = config['headless']
        channel = config['channel']
        page_pool_size = config['page_pool_size']

        async with AsyncCamoufox(headless=headless, channel=channel) as browser:
            context = await browser.new_context()
            self.page_pool = PagePool(browser, context, page_pool_size)

            while not self.stop_event.is_set():
                task_data = await self.task_queue.async_q.get()
                if task_data is None:
                    self.task_queue.async_q.task_done()
                    break

                task_type, future, payload = task_data
                await self._process_task(task_type, future, payload)

            await self.page_pool.cleanup()
            self.page_pool = None

    async def _process_task(self, task_type: TaskType, future: Future, payload: dict[str, Any]) -> None:
        handlers = {
            TaskType.OPEN_PAGE: self._handle_open_page,
            TaskType.CLOSE_PAGE: self._handle_close_page
        }

        handler = handlers.get(task_type)
        if handler is None:
            self.logger.error(f"Invalid task type: {task_type}")
            future.set_exception(ValueError(f"Invalid task type: {task_type}"))
            self.task_queue.async_q.task_done()
            return

        try:
            result = await handler(payload)
            future.set_result(result)
        except Exception as e:
            self.logger.error(f"Error executing task: {e}")
            future.set_exception(e)
        finally:
            self.task_queue.async_q.task_done()

    async def _handle_open_page(self, payload: dict[str, Any]) -> Tuple[Optional[List[Any]], None]:
        url = payload.get("url")
        policy = payload.get("intercept_policy")
        query_params = payload.get("query_params")

        result = await self._open_page(url, policy, query_params)
        return (result, None)

    async def _handle_close_page(self, payload: dict[str, Any]) -> bool:
        page = payload.get("page")
        await self.page_pool.safe_close_page(page)
        return True

    async def _open_page(
        self,
        url: str,
        policy: Optional[InterceptPolicy] = None,
        query_params: Optional[dict[str, Any]] = None
    ) -> Optional[List[Any]]:
        if not is_valid_url(url):
            self.logger.error(f"Invalid URL: {url}")
            return None

        if policy is None:
            self.logger.error(f"Policy is None for URL: {url}")
            return None

        retry_delay = policy.page_delay
        retry_count = policy.retry_count

        for idx in range(retry_count + 1):
            if self.stop_event.is_set():
                self.logger.error(f"Stop event is set for URL: {url}")
                return None

            success, collected_responses = await self._intercept(
                url=url,
                policy=policy,
                query_params=query_params
            )

            if success:
                return collected_responses

            if idx < retry_count:
                await asyncio.sleep(retry_delay)
                continue

            self.logger.error(f"Failed to intercept page {url} after {retry_count} retries")
            return None

    async def _intercept(
        self,
        url: str,
        policy: InterceptPolicy,
        query_params: Optional[dict[str, Any]] = None
    ) -> Tuple[bool, Optional[List[Any]]]:
        intercept_flag = False
        collected_datas: List[Any] = []
        is_resident = policy.has_rules(InterceptType.WS)

        async def _http_request_handler(route, request) -> None:
            try:
                http_rule = policy.find_rule(
                    type=InterceptType.HTTP,
                    url=request.url
                )

                if http_rule and http_rule.sender:
                    overrides = await http_rule.sender.process(request, query_params)
                    if overrides is not None:
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

            http_rule = policy.find_rule(
                type=InterceptType.HTTP,
                url=response.url
            )
            if http_rule is None or http_rule.receiver is None:
                return

            try:
                parsed_data = await http_rule.receiver.process(response)
                if parsed_data is None:
                    return

                collected_datas.append(parsed_data)
            except Exception as e:
                self.logger.error(f"Failed to process response from {response.url} {response.request.method} {http_rule.receiver}: {e}", exc_info=True)

        async def _ws_connect_handler(ws: WebSocket):
            ws_rule = policy.find_rule(
                type=InterceptType.WS,
                url=ws.url
            )
            if not ws_rule or not ws_rule.receiver:
                return

            async def _framereceived_handler(frame):
                try:
                    await ws_rule.receiver.process(frame)
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
            dom_rule = policy.find_rule(type=InterceptType.DOM)
            if dom_rule is None or dom_rule.receiver is None:
                return

            try:
                parsed_data = await dom_rule.receiver.process(await page_context.content())
                if parsed_data is None:
                    return

                collected_datas.append(parsed_data)
            except Exception as e:
                self.logger.error(f"Failed to process page content from {url} {dom_rule.receiver}: {e}", exc_info=True)

        async def _goto_page(page_context, policy: InterceptPolicy) -> None:
            self.logger.debug(f"Goto page {url}")
            start_time = time.time()

            selector = policy.selector
            timeout = policy.timeout

            await page_context.goto(url, wait_until='domcontentloaded', timeout=timeout*1000)
            if selector is not None:
                await page_context.wait_for_selector(selector, timeout=timeout*1000)
            try:
                await page_context.wait_for_load_state('networkidle', timeout=timeout*1000)
            except Exception as e:
                self.logger.error(f"Failed to wait for load state: {e}")

            await self.cloudflare_handler.wait_for_verification(page_context, timeout)

            # elapsed_time = time.time() - start_time
            # remaining_time = policy.page_delay - elapsed_time
            # if remaining_time > 0:
            #     await asyncio.sleep(remaining_time)

            end_time = time.time()
            self.logger.info(f"page loaded ({end_time - start_time}s): {url}")

        async with self.page_pool.acquire(is_resident=is_resident) as page_context:
            if page_context.page is None:
                self.logger.error("Failed to get page (queue empty and max limit reached)")
                return False, None

            try:
                if policy.has_rules(InterceptType.HTTP):
                    if policy.has_senders(InterceptType.HTTP):
                        await page_context.route("**/*", _http_request_handler)

                    if policy.has_receivers(InterceptType.HTTP):
                        page_context.on("response", _http_response_handler)

                    self.logger.debug(f"Register http request and response handler for page: {url}")

                if policy.has_rules(InterceptType.WS):
                    page_context.on("websocket", _ws_connect_handler)
                    collected_datas.append(page_context.page)

                    self.logger.debug(f"Register ws handler for page: {url}")

                await _goto_page(page_context, policy)

                if policy.has_rules(InterceptType.DOM):
                    await _page_content_handler(page_context)

                intercept_flag = True
            except Exception as e:
                self.logger.error(f"Error loading page {url}: {e}", exc_info=True)
            finally:
                if policy.has_rules(InterceptType.HTTP):
                    if policy.has_senders(InterceptType.HTTP):
                        try:
                            await page_context.unroute("**/*", _http_request_handler)
                        except Exception:
                            pass

                    if policy.has_receivers(InterceptType.HTTP):
                        try:
                            page_context.remove_listener("response", _http_response_handler)
                        except Exception:
                            pass

        return intercept_flag, collected_datas