import time
import janus
import asyncio
from enum import Enum
from contextlib import suppress
from core.utils.thread import Thread
from concurrent.futures import Future
from core.utils.singleton import Singleton
from playwright.async_api import WebSocket
from core.browser.page_pool import PagePool
from camoufox.async_api import AsyncCamoufox
from typing import Tuple, List, Optional, Any
from urllib.parse import urlparse
from core.browser.rate_limiter import RateLimiter
from core.config.config_manager import ConfigManager
from core.browser.intercept_monitor import InterceptMonitor
from core.browser.turnstile_solver import TurnstileSolver
from core.browser.intercept_policy import InterceptType, InterceptPolicy

class TaskType(Enum):
    OPEN_PAGE = 1
    CLOSE_PAGE = 2

class Interceptor(Thread, Singleton):
    def __init__(self) -> None:
        super().__init__()
        self.page_pool = None
        self.task_queue: Optional[janus.Queue] = None
        self.turnstile_solver = TurnstileSolver()
        self.rate_limiter = RateLimiter()

    def get_page_pool(self) -> Optional[PagePool]:
        return self.page_pool

    def submit_task(self, task_type: TaskType, **kwargs) -> Optional[Future]:
        future = Future()

        if self.task_queue is None:
            future.set_exception(RuntimeError("Task queue is not initialized"))
            return future

        if self.stop_event.is_set():
            future.set_exception(RuntimeError("Interceptor is stopped"))
            return future

        self.task_queue.sync_q.put((task_type, future, kwargs))
        return future


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
        try:
            await self._async_run_loop()
        finally:
            await self._drain_pending_tasks()

    async def _drain_pending_tasks(self) -> None:
        while True:
            try:
                task_data = self.task_queue.async_q.get_nowait()
            except Exception:
                break

            _, future, _ = task_data
            if not future.done():
                future.set_exception(RuntimeError("Interceptor or browser stopped"))

            self.task_queue.async_q.task_done()

    async def _async_run_loop(self) -> None:
        config = ConfigManager.get_instance().get_config("browser")

        options = config.get("options", {})
        page_pool_size = config['page_pool_size']
        page_limit = config['page_limit']
        viewport = config['viewport']

        while not self.stop_event.is_set():
            intercepted_pages = 0

            async with AsyncCamoufox(**options) as browser:
                context = await browser.new_context(viewport=viewport)
                self.page_pool = PagePool(context, page_pool_size)

                while not self.stop_event.is_set():
                    try:
                        task_data = await asyncio.wait_for(self.task_queue.async_q.get(), timeout=5.0)
                    except asyncio.TimeoutError:
                        continue

                    task_type, future, payload = task_data
                    await self._process_task(task_type, future, payload)
                    self.task_queue.async_q.task_done()

                    intercepted_pages += 1
                    if intercepted_pages >= page_limit:
                        self.logger.info(f"Restarting browser after {intercepted_pages} tasks")
                        break

                self.logger.info(f"Page pool cleanup.")
                self.page_pool = None

    async def _process_task(self, task_type: TaskType, future: Future, payload: dict[str, Any]) -> None:
        try:
            handlers = {
                TaskType.OPEN_PAGE: self._handle_open_page
            }

            handler = handlers.get(task_type)
            if not handler:
                raise ValueError(f"No handler found for task type: {task_type}")

            result = await handler(payload)
            if not future.done():
                future.set_result(result)
        except Exception as e:
            self.logger.error(f"Error processing task {task_type}: {e}", exc_info=True)
            if not future.done():
                future.set_exception(e)

    async def _handle_open_page(self, payload: dict[str, Any]) -> Tuple[Optional[List[Any]], None]:
        url = payload.get("url")
        policy = payload.get("intercept_policy")
        query_params = payload.get("query_params")

        result = await self._open_page(url, policy, query_params)
        return (result, None)

    async def _register_handlers(
        self,
        page_context: Any,
        policy: InterceptPolicy,
        monitor: InterceptMonitor,
        collected_datas: List[Any],
        query_params: Optional[dict[str, Any]] = None
    ) -> Tuple[Any, Any, Any]:

        http_request_handler = None
        http_response_handler = None
        ws_connect_handler = None

        if policy.has_rules(InterceptType.HTTP):
            if policy.has_senders(InterceptType.HTTP):
                async def _http_request_handler(route, request) -> None:
                    try:
                        rule = policy.find_rule(InterceptType.HTTP, request.url)
                        if rule and rule.sender:
                            overrides = await rule.sender.process(request, query_params)

                            if overrides is not None:
                                await route.continue_(**overrides)
                                return
                    except Exception as e:
                        self.logger.error(f"Failed to send request: {e}")

                    try:
                        if policy.debug:
                            self.logger.info(f"Continuing request without modification: {request.url}")
                        await route.continue_()
                    except Exception as e:
                        self.logger.error(f"Failed to continue request: {e}")
                        with suppress(Exception):
                            await route.abort("failed")

                await page_context.route("**/*", _http_request_handler)
                http_request_handler = _http_request_handler

            if policy.has_receivers(InterceptType.HTTP):
                async def _http_response_handler(response) -> None:
                    if not response.ok:
                        if policy.debug:
                            self.logger.info(f"Skipping non-OK response: {response.url} {response.status}")
                        return

                    http_rule = policy.find_rule(
                        type=InterceptType.HTTP,
                        url=response.url
                    )
                    if http_rule is None or http_rule.receiver is None:
                        if policy.debug:
                            self.logger.warning(f"No receiver found for HTTP rule: {response.url}")
                        return

                    try:
                        parsed_data = await http_rule.receiver.process(response)
                        if parsed_data is None:
                            return

                        collected_datas.append(parsed_data)
                        monitor.mark_completed(response.url)
                    except Exception as e:
                        self.logger.error(f"Failed to process response from {response.url} {response.request.method} {http_rule.receiver}: {e}", exc_info=True)

                page_context.on("response", _http_response_handler)
                http_response_handler = _http_response_handler

        if policy.has_rules(InterceptType.WS):
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

            page_context.on("websocket", _ws_connect_handler)
            collected_datas.append(page_context)
            ws_connect_handler = _ws_connect_handler

        return http_request_handler, http_response_handler, ws_connect_handler

    async def _process_dom(
        self,
        page_context: Any,
        url: str,
        policy: InterceptPolicy,
        collected_datas: List[Any]
    ) -> None:
        if not policy.has_rules(InterceptType.DOM):
            return

        dom_rule = policy.find_rule(type=InterceptType.DOM)
        if dom_rule is None or dom_rule.receiver is None:
            if policy.debug:
                self.logger.warning(f"No receiver found for DOM rule: {url}")
            return

        try:
            parsed_data = await dom_rule.receiver.process(
                page_context=page_context,
                url=url,
                timeout=policy.timeout
            )

            if parsed_data is None:
                return

            collected_datas.append(parsed_data)
        except Exception as e:
            self.logger.error(f"Failed to process page content from {url} {dom_rule.receiver}: {e}", exc_info=True)

    def _is_valid_url(self, url: str) -> bool:
        if not url or not isinstance(url, str):
            return False
        try:
            res = urlparse(url)
            return bool(res.scheme and res.netloc)
        except Exception:
            return False

    async def _open_page(
        self,
        url: str,
        policy: Optional[InterceptPolicy] = None,
        query_params: Optional[dict[str, Any]] = None
    ) -> Optional[List[Any]]:
        if policy is None:
            self.logger.error(f"Policy is None for URL: {url}")
            return None

        if not self._is_valid_url(url):
            self.logger.error(f"Invalid URL: {url}")
            return None

        retry_count = policy.retry_count
        for idx in range(retry_count + 1):
            if self.stop_event.is_set():
                self.logger.info(f"Stop event is set for URL: {url}")
                return None

            await self.rate_limiter.throttle(url, policy.page_delay)

            success, collected_responses = await self._intercept(
                url=url,
                policy=policy,
                query_params=query_params
            )

            if success:
                return collected_responses

            if idx >= retry_count:
                self.logger.error(f"Failed to intercept page {url} after {retry_count} retries")
                return None

            self.logger.info(f"Retrying to intercept page {url} (attempt {idx + 1}/{retry_count})")

    async def _intercept(
        self,
        url: str,
        policy: InterceptPolicy,
        query_params: Optional[dict[str, Any]] = None
    ) -> Tuple[bool, Optional[List[Any]]]:
        collected_datas: List[Any] = []
        timeout = policy.timeout

        try:
            async with self.page_pool.acquire(timeout) as page_context:
                http_request_handler = None
                http_response_handler = None

                try:
                    intercept_monitor = InterceptMonitor(policy, InterceptType.HTTP)

                    (
                        http_request_handler,
                        http_response_handler,
                        _
                    ) = await self._register_handlers(
                        page_context,
                        policy,
                        intercept_monitor,
                        collected_datas,
                        query_params
                    )

                    start_time = time.time()

                    response = await page_context.goto(url, wait_until='domcontentloaded', timeout=timeout*1000)
                    if response is None:
                        self.logger.warning(f"Navigation to {url} returned None, no response available")
                        return False, collected_datas

                    if await self.rate_limiter.is_rate_limited(response):
                        self.rate_limiter.activate_backoff(url)
                        return False, collected_datas

                    if not await self.turnstile_solver.solve(page_context, timeout=timeout):
                        self.logger.error(f"Failed to solve turnstile for URL: {url}")
                        return False, collected_datas

                    await intercept_monitor.wait(timeout)

                    elapsed_time = time.time() - start_time
                    self.logger.info(f"Page loaded: {url} in {elapsed_time:.2f}s")

                    await self._process_dom(page_context, url, policy, collected_datas)
                    self.rate_limiter.reset_backoff(url)

                    if policy.has_rules(InterceptType.WS):
                        page_context.detach()

                    return True, collected_datas
                except Exception as e:
                    self.logger.error(f"Error loading page {url}: {e}", exc_info=True)

        except asyncio.TimeoutError:
            self.logger.error(f"Timeout while acquiring page for URL: {url}")
        except Exception as e:
            self.logger.error(f"Error loading page {url}: {e}", exc_info=True)
        return False, collected_datas
