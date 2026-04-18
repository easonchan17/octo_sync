import time
import janus
import asyncio
from enum import Enum
from urllib.parse import urlparse
from core.utils.thread import Thread
from concurrent.futures import Future
from core.utils.singleton import Singleton
from core.browser.page_pool import PagePool
from camoufox.async_api import AsyncCamoufox
from typing import Tuple, Optional, Any
from core.browser.security import RateLimiter
from core.config.config_manager import ConfigManager
from core.browser.hooks import HookChain, HookContext, HttpHook, WsHook, DomHook, TurnstileHook, JsHook
from core.browser.intercept_result_set import InterceptResultSet, FetchState
from core.browser.intercept_policy import InterceptType, InterceptPolicy


class TaskType(Enum):
    OPEN_PAGE = 1
    CLOSE_PAGE = 2


class Interceptor(Thread, Singleton):
    def __init__(self) -> None:
        super().__init__()
        self.page_pool = None
        self.task_queue: Optional[janus.Queue] = None
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
        # self.logger.info(f"Submitted task: {task_type} {kwargs}")
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
        except Exception as e:
            if "Connection closed" not in str(e) and "TargetClosed" not in str(e):
                raise
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

    def _asyncio_exception_handler(self, loop: Any, context: dict) -> None:
        exc = context.get("exception")

        if exc is not None:
            exc_name = type(exc).__name__
            if "TargetClosedError" in exc_name or "ConnectionClosed" in exc_name:
                return

        task_info = ""
        task_or_future = context.get("task") or context.get("future")
        if task_or_future is not None:
            try:
                if hasattr(task_or_future, "get_coro"):
                    task_info = f" | Coro: {task_or_future.get_coro()}"
                else:
                    task_info = f" | Task/Future: {task_or_future!r}"
            except Exception:
                pass

        msg = context.get("message", "Unhandled exception")
        self.logger.error(
            f"Asyncio unhandled: {msg}{task_info}",
            exc_info=exc if exc is not None else False
        )

    async def _async_run_loop(self) -> None:
        loop = asyncio.get_running_loop()
        loop.set_exception_handler(self._asyncio_exception_handler)

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
                    await self._run_with_stop_check(task_type, future, payload)
                    self.task_queue.async_q.task_done()

                    intercepted_pages += 1
                    if intercepted_pages >= page_limit:
                        self.logger.info(f"Restarting browser after {intercepted_pages} tasks")
                        break

                self.logger.info(f"Page pool cleanup.")
                self.page_pool = None

    async def _run_with_stop_check(self, task_type: TaskType, future: Future, payload: dict[str, Any]) -> None:
        process_task = asyncio.create_task(self._process_task(task_type, future, payload))
        while not process_task.done():
            if self.stop_event.is_set():
                process_task.cancel()
                try:
                    await process_task
                except (asyncio.CancelledError, Exception):
                    pass
                if not future.done():
                    future.set_exception(RuntimeError("Interceptor stopped"))
                return
            await asyncio.sleep(0.5)

        if not process_task.cancelled():
            process_task.exception()

    async def _process_task(self, task_type: TaskType, future: Future, payload: dict[str, Any]) -> None:
        try:
            handlers = {
                TaskType.OPEN_PAGE: self._handle_open_page
            }

            handler = handlers.get(task_type)
            if not handler:
                raise ValueError(f"No handler found for task type: {task_type}")

            result_set = await handler(payload)
            if not future.done():
                future.set_result(result_set)
        except Exception as e:
            self.logger.error(f"Error processing task {task_type}: {e}", exc_info=True)
            if not future.done():
                future.set_exception(e)

    async def _handle_open_page(self, payload: dict[str, Any]) -> Optional[InterceptResultSet]:
        url = payload.get("url")
        policy = payload.get("intercept_policy")
        query_params = payload.get("query_params")

        return await self._open_page(url, policy, query_params)

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
    ) -> Optional[InterceptResultSet]:
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

            success, result_set = await self._intercept(
                url=url,
                policy=policy,
                query_params=query_params
            )

            if success:
                return result_set

            if idx >= retry_count:
                self.logger.error(f"Failed to intercept page {url} after {idx + 1} attempts")
                return None

            self.logger.info(f"Retrying to intercept page {url} (attempt {idx + 1}/{retry_count})")

    async def _intercept(
        self,
        url: str,
        policy: InterceptPolicy,
        query_params: Optional[dict[str, Any]] = None
    ) -> Tuple[bool, InterceptResultSet]:
        result_set = InterceptResultSet()
        timeout = policy.timeout

        try:
            async with self.page_pool.acquire(timeout) as page_context:
                try:
                    hooks = [TurnstileHook()]
                    if policy.has_rules(InterceptType.HTTP):
                        hooks.append(HttpHook())
                    if policy.has_rules(InterceptType.JS):
                        hooks.append(JsHook())
                    if policy.has_rules(InterceptType.DOM):
                        hooks.append(DomHook())
                    if policy.has_rules(InterceptType.WS):
                        hooks.append(WsHook())
                    hook_chain = HookChain(hooks)

                    ctx = HookContext(
                        page_context=page_context,
                        target_url=url,
                        policy=policy,
                        query_params=query_params,
                        result_set=result_set,
                    )

                    await hook_chain.setup(ctx)

                    start_time = time.time()
                    page_context.request._impl_obj._timeout_settings.set_default_timeout(timeout * 1000)
                    response = await page_context.goto(url, wait_until='domcontentloaded', timeout=timeout * 1000)

                    if response is None:
                        self.logger.warning(f"Navigation to {url} returned None, no response available")
                        return False, result_set

                    if await self.rate_limiter.is_rate_limited(response):
                        self.rate_limiter.activate_backoff(url, status=response.status)
                        return False, result_set

                    try:
                        success = await hook_chain.execute(ctx)
                    finally:
                        await hook_chain.destroy(ctx)

                    if not success:
                        return False, result_set

                    self.rate_limiter.reset_backoff(url)

                    elapsed_time = time.time() - start_time
                    self.logger.info(f"Page loaded: {url} in {elapsed_time:.2f}s")

                    return True, result_set
                except Exception as e:
                    self.logger.error(f"Error loading page {url}: {e}", exc_info=True)

        except asyncio.TimeoutError:
            self.logger.error(f"Timeout while acquiring page for URL: {url}")
        except Exception as e:
            self.logger.error(f"Error loading page {url}: {e}", exc_info=True)
        return False, result_set
