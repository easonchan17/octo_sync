import json
from contextlib import suppress
from typing import Optional
from core.browser.hooks.latch import SignalLatch
from core.browser.intercept_strategy import InterceptType
from core.browser.hooks.base_hook import BaseHook, HookContext

class JsHook(BaseHook):
    TRACE_ROUTE_PATTERN = "**/__app_trace__/**"

    def __init__(self) -> None:
        super().__init__()
        self._latch: Optional[SignalLatch] = None
        self._trace_handler = None

    async def setup(self, ctx: HookContext) -> None:
        js_rule = ctx.strategy.find_rule(type=InterceptType.JS)
        if js_rule is None:
            return

        self._latch = SignalLatch()

        async def _trace_handler(route, request) -> None:
            try:
                if js_rule.pattern and not request.url.endswith(js_rule.pattern):
                    return

                if not request.post_data:
                    self.logger.warning(f"Empty trace body from: {request.url}")
                    return

                json_data = json.loads(request.post_data)
                data = json_data.get("data")
                if not data:
                    self.logger.warning(f"Empty trace data from: {request.url}")
                    return

                if js_rule.on_trace:
                    data = await js_rule.on_trace(ctx, data)
                    if data is None:
                        self.logger.info(f"Discarded data for: {request.url}")
                        return

                ctx.result_set.set(1, data)
                self._latch.mark_completed()
                self.logger.info(f"Data captured from: {request.url}")
            except Exception as e:
                self.logger.error(f"Failed to process data from: {request.url}: {e}", exc_info=True)
            finally:
                with suppress(Exception):
                    await route.fulfill(status=200, body="ok")

        await ctx.page_context.route(self.TRACE_ROUTE_PATTERN, _trace_handler)
        self._trace_handler = _trace_handler

    async def destroy(self, ctx: HookContext) -> None:
        with suppress(Exception):
            if self._trace_handler:
                await ctx.page_context.unroute(self.TRACE_ROUTE_PATTERN, self._trace_handler)

    async def execute(self, ctx: HookContext) -> bool:
        if self._latch is None:
            return True

        await self._latch.wait(ctx.strategy.timeout)
        return True
