import os, signal, janus, asyncio, psutil, random, time
from contextlib import suppress
from functools import cache
from urllib.parse import urlparse
from core.utils.thread import Thread
from concurrent.futures import Future
from core.browser.page_pool import PagePool
from camoufox.async_api import AsyncCamoufox
from core.browser.security import RateLimiter
from core.config.config_manager import get_config_manager
from core.types.enums import SiteName
from typing import Tuple, Optional, Any, Dict, List
from playwright._impl._errors import TimeoutError as PlaywrightTimeoutError
from core.browser.hooks import HookChain, HookContext, HttpHook, WsHook, DomHook, TurnstileHook, JsHook, AssetHook
from core.browser.intercept_strategy import InterceptType, InterceptStrategy
from core.browser.intercept_result_set import InterceptResultSet

class Interceptor(Thread):
    def __init__(
        self,
        sites: List[str],
        request_interval: float,
        launch_options: Dict,
        viewport: Dict,
        page_pool_size: int,
        sys_mem_threshold: float,
        failure_threshold: int,
        addons: Optional[list]
    ) -> None:
        super().__init__()
        self.page_pool = None

        self.sites = set(sites)
        self.task_queue: Optional[janus.Queue] = None
        self.sub_queues: Dict[str, asyncio.Queue] = {}
        self.sub_workers: Dict[str, asyncio.Task] = {}
        self.fail_counts: Dict[str, int] = {}

        self.rate_limiter = RateLimiter(base_interval=request_interval)
        self.launch_options = launch_options
        self.viewport = viewport
        self.page_pool_size = page_pool_size
        self.sys_mem_threshold = sys_mem_threshold
        self.failure_threshold = failure_threshold
        self.addons = addons or []

    def submit(self, url: str, strategy: InterceptStrategy, site_name: str) -> Optional[Future]:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            self.logger.error(f"Invalid url: {url}")
            return None

        if site_name not in self.sites:
            self.logger.error(f"Unsupported site_name: {site_name}")
            return None

        if self.task_queue is None:
            self.logger.error("Task queue is not initialized")
            return None

        if self.stop_event.is_set():
            self.logger.error("Interceptor is stopped")
            return None

        future = Future()
        self.task_queue.sync_q.put((future, url, strategy, site_name))
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
            loop.run_until_complete(asyncio.sleep(0.1))
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

        self.sub_queues = {site: asyncio.Queue() for site in self.sites}
        self.fail_counts = {site: 0 for site in self.sites}

        while not self.stop_event.is_set():
            async with AsyncCamoufox(**self.launch_options, addons=self.addons) as browser:
                context = await browser.new_context(viewport=self.viewport)
                self.page_pool = PagePool(context, self.page_pool_size)

                recycle_event = asyncio.Event()

                self.sub_workers = {
                    site: asyncio.create_task(self._run_worker(sub_queue, recycle_event))
                    for site, sub_queue in self.sub_queues.items()
                }

                dispatcher = asyncio.create_task(self._dispatch_loop(recycle_event))
                await self._wait_for_shutdown_signal(recycle_event)

                dispatcher.cancel()
                with suppress(asyncio.CancelledError):
                    await dispatcher

                await asyncio.gather(*self.sub_workers.values(), return_exceptions=True)
                self.logger.info("Page pool cleanup")
                self.page_pool = None

    async def _wait_for_shutdown_signal(self, recycle_event: asyncio.Event) -> None:
        async def wait_stop():
            while not self.stop_event.is_set():
                await asyncio.sleep(0.5)

        stop_task = asyncio.create_task(wait_stop())
        recycle_task = asyncio.create_task(recycle_event.wait())

        try:
            await asyncio.wait(
                [stop_task, recycle_task],
                return_when=asyncio.FIRST_COMPLETED
            )

        finally:
            for task in (stop_task, recycle_task):
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task

    async def _dispatch_loop(self, recycle_event: asyncio.Event) -> None:
        while not self.stop_event.is_set() and not recycle_event.is_set():
            try:
                task_data = await asyncio.wait_for(self.task_queue.async_q.get(), timeout=5.0)
            except asyncio.TimeoutError:
                continue

            _, _, _, site_name = task_data
            await self.sub_queues[site_name].put(task_data)
            self.task_queue.async_q.task_done()

    async def _run_worker(self, sub_queue: asyncio.Queue, recycle_event: asyncio.Event) -> None:
        while not self.stop_event.is_set() and not recycle_event.is_set():
            try:
                task_data = await asyncio.wait_for(sub_queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            start_time = time.perf_counter()

            await self._run_with_stop_check(task_data)
            sub_queue.task_done()

            cost_time = time.perf_counter() - start_time
            self.logger.info(f"Task cost time {cost_time:.3f} s")

            if self._should_recycle():
                recycle_event.set()
                break

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

            future, _, _, _ = task_data
            if not future.done():
                future.set_exception(RuntimeError("Interceptor or browser stopped"))

            self.task_queue.async_q.task_done()

        for sub_queue in self.sub_queues.values():
            while True:
                try:
                    task_data = sub_queue.get_nowait()
                except Exception:
                    break

                future, _, _, _ = task_data
                if not future.done():
                    future.set_exception(RuntimeError("Interceptor or browser stopped"))

                sub_queue.task_done()

    def _asyncio_exception_handler(self, loop: Any, context: dict) -> None:
        exc = context.get("exception")

        if exc is not None:
            exc_name = type(exc).__name__
            if "TargetClosedError" in exc_name or "ConnectionClosed" in exc_name:
                return

        if "Task was destroyed but it is pending" in context.get("message", ""):
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

    async def _run_with_stop_check(self, task_data: Tuple) -> None:
        process_task = asyncio.create_task(self._process_task(task_data))
        while not process_task.done():
            if self.stop_event.is_set():
                process_task.cancel()

                try:
                    await process_task
                except (asyncio.CancelledError, Exception):
                    pass

                future, _, _, _ = task_data
                if not future.done():
                    future.set_exception(RuntimeError("Interceptor stopped"))

                return

            await asyncio.sleep(0.5)

        if not process_task.cancelled():
            process_task.exception()

    async def _process_task(self, task_data: Tuple) -> None:
        try:
            future, url, strategy, site_name = task_data
            success, result_set = await self._intercept(url=url, strategy=strategy)

            if success:
                if self.fail_counts[site_name] > 0:
                    self.logger.info(f"[{site_name}] Recovered after {self.fail_counts[site_name]} consecutive failures")
                self.fail_counts[site_name] = 0
            else:
                self.fail_counts[site_name] += 1
                self.logger.error(f"[{site_name}] Consecutive failures: {self.fail_counts[site_name]}")
                if not self.stop_event.is_set() and any(v >= self.failure_threshold for v in self.fail_counts.values()):
                    self.logger.critical(f"All sites reached failure threshold ({self.failure_threshold}), restarting process...")
                    os.kill(os.getpid(), signal.SIGTERM)

            if not future.done():
                future.set_result(result_set if success else None)
        except Exception as e:
            self.logger.error(f"Error processing task: {e}", exc_info=True)
            if not future.done():
                future.set_exception(e)

    async def _intercept(self, url: str, strategy: InterceptStrategy) -> Tuple[bool, InterceptResultSet]:
        await self.rate_limiter.throttle(url)

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
                if strategy.has_rules(InterceptType.ASSET):
                    hooks.append(AssetHook())
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
                    page_context.request._impl_obj._timeout_settings.set_default_timeout(timeout * 1000)
                    response = await page_context.goto(url, wait_until='commit', timeout=timeout * 1000)

                    if response is None:
                        self.logger.warning(f"No response: {url}")
                    elif await self.rate_limiter.is_rate_limited(response):
                        self.rate_limiter.activate_backoff(url, status=response.status)
                    else:
                        ctx.response = response
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


@cache
def get_interceptor() -> Interceptor:
    config = get_config_manager().get_config("browser")
    return Interceptor(
        sites=[SiteName.FOTMOB.value, SiteName.ODDSPORTAL.value],
        request_interval=config["request_interval"],
        launch_options=config["launch_options"],
        viewport=config["viewport"],
        page_pool_size=config["page_pool_size"],
        sys_mem_threshold=config["sys_mem_threshold"],
        failure_threshold=config["failure_threshold"],
        addons=[os.path.abspath(p) for p in config.get("addons", [])],
    )
