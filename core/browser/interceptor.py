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
from core.utils.string_utils import is_valid_url
from core.browser.rate_limiter import RateLimiter
from core.config.config_manager import ConfigManager
from core.browser.intercept_monitor import InterceptMonitor
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
        self.rate_limiter = RateLimiter()

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

            self.logger.info(f"Page pool cleanup. Active pages remaining: {self.page_pool.get_count()}")
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

        result = await handler(payload)
        future.set_result(result)
        self.task_queue.async_q.task_done()

    async def _handle_open_page(self, payload: dict[str, Any]) -> Tuple[Optional[List[Any]], None]:
        url = payload.get("url")
        policy = payload.get("intercept_policy")
        query_params = payload.get("query_params")

        result = await self._open_page(url, policy, query_params)
        return (result, None)

    async def _handle_close_page(self, payload: dict[str, Any]) -> bool:
        page_id = payload.get("page_id")
        await self.page_pool.remove_resident_page(page_id)
        return True

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
            collected_datas.append(page_context.id)
            ws_connect_handler = _ws_connect_handler

        return http_request_handler, http_response_handler, ws_connect_handler


    async def _unregister_handlers(
        page_context: Any,
        http_request_handler: Optional[Any] = None,
        http_response_handler: Optional[Any] = None,
        ws_connect_handler: Optional[Any] = None
    ) -> None:
        if http_request_handler:
            try:
                await page_context.unroute("**/*", http_request_handler)
            except Exception:
                pass

        if http_response_handler:
            try:
                page_context.remove_listener("response", http_response_handler)
            except Exception:
                pass

        if ws_connect_handler:
            try:
                page_context.remove_listener("websocket", ws_connect_handler)
            except Exception:
                pass

    async def _process_dom_content(
        self,
        page_context: Any,
        policy: InterceptPolicy,
        collected_datas: List[Any]
    ) -> None:
        if not policy.has_rules(InterceptType.DOM):
            return

        dom_rule = policy.find_rule(type=InterceptType.DOM)
        if dom_rule is None or dom_rule.receiver is None:
            if policy.debug:
                self.logger.warning(f"No receiver found for DOM rule: {policy.url}")
            return

        try:
            content = await page_context.content()
            parsed_data = await dom_rule.receiver.process(content)
            if parsed_data is None:
                return

            collected_datas.append(parsed_data)
        except Exception as e:
            self.logger.error(f"Failed to process page content from {policy.url} {dom_rule.receiver}: {e}", exc_info=True)

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

    async def _intercept(
        self,
        url: str,
        policy: InterceptPolicy,
        query_params: Optional[dict[str, Any]] = None
    ) -> Tuple[bool, Optional[List[Any]]]:
        collected_datas: List[Any] = []

        is_resident = policy.has_rules(InterceptType.WS)
        timeout = policy.timeout

        try:
            async with self.page_pool.acquire(is_resident, timeout) as page_context:
                try:
                    monitor = InterceptMonitor(policy, InterceptType.HTTP)

                    (
                        http_request_handler,
                        http_response_handler,
                        _
                    ) = await self._register_handlers(
                        page_context,
                        policy,
                        monitor,
                        collected_datas,
                        query_params
                    )

                    response = await page_context.goto(url, wait_until='domcontentloaded', timeout=timeout*1000)
                    self.logger.info(f"Page loaded: {url}")

                    is_rate_limited, _ = await self.rate_limiter.is_rate_limited(response, page_context)
                    if is_rate_limited:
                        self.rate_limiter.activate_backoff(url)
                        return False, collected_datas

                    await self._process_dom_content(page_context, policy, collected_datas)
                    await monitor.wait(timeout)

                    self.rate_limiter.reset_backoff(url)
                    return True, collected_datas

                except Exception as e:
                    self.logger.error(f"Error loading page {url}: {e}", exc_info=True)
                finally:
                    await self._unregister_handlers(
                        page_context,
                        http_request_handler,
                        http_response_handler
                    )

        except asyncio.TimeoutError:
            self.logger.error(f"Timeout while acquiring page for URL: {url}")
        return False, collected_datas
