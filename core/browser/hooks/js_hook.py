import re
import json
from contextlib import suppress
from typing import Optional
from urllib.parse import urlparse
from core.browser.hooks.latch import SignalLatch
from core.browser.intercept_strategy import InterceptType
from core.browser.hooks.base_hook import BaseHook, HookContext

class JsHook(BaseHook):
    TRACE_ROUTE_PATTERN = "**/__app_trace__/**"

    def __init__(self) -> None:
        super().__init__()
        self._latch: Optional[SignalLatch] = None
        self._trace_handler = None
        self._js_inject_handler = None

    async def setup(self, ctx: HookContext) -> None:
        js_rule = ctx.strategy.find_rule(type=InterceptType.JS)
        if js_rule is None or not js_rule.hook_script:
            return

        self._latch = SignalLatch()

        async def _trace_handler(route, request) -> None:
            try:
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

        async def _js_inject_handler(route, request) -> None:
            response = None
            fulfilled = False

            try:
                if request.resource_type != "document":
                    return

                response = await route.fetch(
                    headers=await request.all_headers(),
                    max_redirects=0,
                    timeout=ctx.strategy.timeout * 1000
                )

                if response.status in (301, 302, 303, 307, 308):
                    location = response.headers.get('location')
                    if location is None:
                        self.logger.error(f"Redirect response without location header for: {request.url}")
                        return

                    response = await ctx.page_context.request.get(location)

                if response.status in range(200, 300):
                    def inject_script_to_head(body: str, script: str) -> str:
                        script_tag = f"<script>{script}</script>"

                        injected_body, _ = re.subn(
                            r'(<head[^>]*>)',
                            lambda m: m.group(1) + script_tag,
                            body,
                            count=1,
                            flags=re.IGNORECASE
                        )

                        return injected_body

                    await route.fulfill(
                        response=response,
                        body=inject_script_to_head(await response.text(), js_rule.hook_script),
                        headers=response.headers
                    )
                    self.logger.info(f"Injected hook script into: {request.url}")

                    fulfilled = True
            except Exception as e:
                self.logger.error(f"Failed to inject hook script into: {request.url}: {e}", exc_info=True)
            finally:
                if response is None:
                    with suppress(Exception):
                        await route.fallback()
                elif not fulfilled:
                    with suppress(Exception):
                        await route.fulfill(response=response)

        await ctx.page_context.route(self.TRACE_ROUTE_PATTERN, _trace_handler)
        await ctx.page_context.route("**/*", _js_inject_handler)
        self._trace_handler = _trace_handler
        self._js_inject_handler = _js_inject_handler


    async def destroy(self, ctx: HookContext) -> None:
        with suppress(Exception):
            if self._trace_handler:
                await ctx.page_context.unroute(self.TRACE_ROUTE_PATTERN, self._trace_handler)
        with suppress(Exception):
            if self._js_inject_handler:
                await ctx.page_context.unroute("**/*", self._js_inject_handler)


    async def execute(self, ctx: HookContext) -> bool:
        if self._latch is None:
            return True

        await self._latch.wait(ctx.strategy.timeout)
        return True
