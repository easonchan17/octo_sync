import janus, asyncio, psutil, random, time
from playwright._impl._errors import TimeoutError as PlaywrightTimeoutError
from urllib.parse import urlparse
from core.utils.thread import Thread
from concurrent.futures import Future
from core.browser.page_pool import PagePool
from camoufox.async_api import AsyncCamoufox
from typing import Tuple, Optional, Any, Dict
from core.browser.security import RateLimiter
from core.browser.hooks import HookChain, HookContext, HttpHook, WsHook, DomHook, TurnstileHook, JsHook
from core.browser.intercept_strategy import InterceptType, InterceptStrategy
from core.browser.intercept_result_set import InterceptResultSet

class Interceptor(Thread):
    def __init__(self, request_interval: float, launch_options: Dict, viewport: Dict, page_pool_size: int = 5, sys_mem_threshold: float = 95) -> None:
        super().__init__()
        self.page_pool = None
        self.task_queue: Optional[janus.Queue] = None
        self.rate_limiter = RateLimiter(base_interval=request_interval)
        self.launch_options = launch_options
        self.viewport = viewport
        self.page_pool_size = page_pool_size
        self.sys_mem_threshold = sys_mem_threshold

    def submit(self, url: str, strategy: InterceptStrategy) -> Optional[Future]:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            self.logger.error(f"Invalid url: {url}")
            return None

        if self.task_queue is None:
            self.logger.error("Task queue is not initialized")
            return None

        if self.stop_event.is_set():
            self.logger.error("Interceptor is stopped")
            return None

        future = Future()
        self.task_queue.sync_q.put((future, url, strategy))
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

    async def _async_run_loop(self) -> None:
        loop = asyncio.get_running_loop()
        loop.set_exception_handler(self._asyncio_exception_handler)

        while not self.stop_event.is_set():
            intercepted_pages = 0

            async with AsyncCamoufox(**self.launch_options) as browser:
                context = await browser.new_context(viewport=self.viewport)
                self.page_pool = PagePool(context, self.page_pool_size)

                while not self.stop_event.is_set():
                    try:
                        task_data = await asyncio.wait_for(self.task_queue.async_q.get(), timeout=5.0)
                    except asyncio.TimeoutError:
                        continue

                    start_time = time.perf_counter()

                    future, url, strategy = task_data
                    await self._run_with_stop_check(future, url, strategy)
                    self.task_queue.async_q.task_done()

                    cost_time = time.perf_counter() - start_time
                    self.logger.info(f"Task cost time {cost_time:.3f} s")

                    intercepted_pages += 1
                    if self._should_recycle():
                        self.logger.warning(f"Restarting browser after {intercepted_pages} tasks")
                        break

                self.logger.info(f"Page pool cleanup")
                self.page_pool = None

    def _should_recycle(self):
        mem = psutil.virtual_memory()

        if mem.percent >= self.sys_mem_threshold:
            self.logger.warning(f"Memory usage at {mem.percent}%, restarting browser")
            return True

        return False

    async def _drain_pending_tasks(self) -> None:
        while True:
            try:
                task_data = self.task_queue.async_q.get_nowait()
            except Exception:
                break

            future, _, _ = task_data
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

    async def _run_with_stop_check(self, future: Future, url: str, strategy: InterceptStrategy) -> None:
        process_task = asyncio.create_task(self._process_task(future, url, strategy))
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

    async def _process_task(self, future: Future, url: str, strategy: InterceptStrategy) -> None:
        try:
            result_set = await self._open_page(url, strategy)
            if not future.done():
                future.set_result(result_set)
        except Exception as e:
            self.logger.error(f"Error processing task: {e}", exc_info=True)
            if not future.done():
                future.set_exception(e)

    async def _open_page(self, url: str, strategy: InterceptStrategy) -> Optional[InterceptResultSet]:
        await self.rate_limiter.throttle(url)

        success, result_set = await self._intercept(url=url, strategy=strategy)
        if not success:
            return None

        return result_set

    async def _intercept(self, url: str, strategy: InterceptStrategy) -> Tuple[bool, InterceptResultSet]:
        result_set = InterceptResultSet()
        timeout = strategy.timeout
        success = False

        try:
            async with self.page_pool.acquire(timeout) as page_context:
                hooks = [TurnstileHook()]
                if strategy.has_rules(InterceptType.HTTP):
                    hooks.append(HttpHook())
                if strategy.has_rules(InterceptType.JS):
                    hooks.append(JsHook())
                if strategy.has_rules(InterceptType.DOM):
                    hooks.append(DomHook())
                if strategy.has_rules(InterceptType.WS):
                    hooks.append(WsHook())
                hook_chain = HookChain(hooks)

                ctx = HookContext(
                    page_context=page_context,
                    target_url=url,
                    strategy=strategy,
                    result_set=result_set,
                )

                try:
                    await hook_chain.setup(ctx)
                    page_context.set_default_timeout(timeout * 1000)
                    response = await page_context.goto(url, wait_until='domcontentloaded', timeout=timeout * 1000)

                    if response is None:
                        self.logger.warning(f"No response: {url}")
                    elif await self.rate_limiter.is_rate_limited(response):
                        self.rate_limiter.activate_backoff(url, status=response.status)
                    else:
                        success = await hook_chain.execute(ctx)
                finally:
                    await hook_chain.destroy(ctx)

        except (TimeoutError, PlaywrightTimeoutError) as e:
            self.rate_limiter.activate_backoff(url, status=-1)
            self.logger.error(f"Failed to load page {url}: {e}")
        except Exception as e:
            self.rate_limiter.activate_backoff(url, status=-2)
            self.logger.error(f"Failed to load page {url}: {e}")

        if success:
            self.rate_limiter.reset_backoff(url)
            self.logger.info(f"Page loaded: {url}")
            await asyncio.sleep(random.uniform(1, 3))

        return success, result_set
