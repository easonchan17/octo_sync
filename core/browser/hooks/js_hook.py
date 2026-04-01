import json
from typing import Optional
from core.browser.hooks.latch import SignalLatch
from core.browser.intercept_policy import InterceptType
from core.browser.hooks.base_hook import BaseHook, HookContext

TRACE_ROUTE_PATTERN = "**/__app_trace__/**"

class JsHook(BaseHook):
    def __init__(self) -> None:
        super().__init__()
        self._latch: Optional[SignalLatch] = None

    async def setup(self, ctx: HookContext) -> None:
        js_rule = ctx.policy.find_rule(type=InterceptType.JS)
        if js_rule is None or not js_rule.hook_script:
            return

        self._latch = SignalLatch()

        async def _trace_handler(route, request) -> None:
            try:
                json_data = json.loads(request.post_data)
                ctx.result_set.set(1, json_data)
                self.logger.info(f"Trace data captured from: {request.url}")
            except Exception as e:
                self.logger.error(f"Failed to process trace data from: {request.url}: {e}", exc_info=True)
            finally:
                await route.fulfill(status=200, body="ok")
                self._latch.mark_completed()
                try:
                    await ctx.page_context.unroute(TRACE_ROUTE_PATTERN, _trace_handler)
                except Exception:
                    pass

        await ctx.page_context.route(TRACE_ROUTE_PATTERN, _trace_handler)

        async def _js_inject_handler(route, request) -> None:
            if request.resource_type != "document":
                await route.fallback()
                return

            try:
                response = await route.fetch(max_redirects=0)
                if response.status in (301, 302, 303, 307, 308):
                    self.logger.info(f"Redirect ({response.status}) detected for: {request.url}, letting browser follow")
                    await route.fallback()
                    return

                body = await response.text()
                script_tag = f"<script>{js_rule.hook_script}</script>"
                modified_body = body.replace("<head>", f"<head>{script_tag}", 1)
                await route.fulfill(response=response, body=modified_body)
                self.logger.info(f"Injected hook script into: {request.url}")
            except Exception as e:
                self.logger.error(f"Failed to inject hook script into: {request.url}: {e}", exc_info=True)
                await route.fallback()

            # try:
            #     await ctx.page_context.unroute("**/*", _js_inject_handler)
            # except Exception:
            #     pass

        await ctx.page_context.route("**/*", _js_inject_handler)

    async def execute(self, ctx: HookContext) -> bool:
        if self._latch is None:
            return True

        await self._latch.wait(ctx.policy.timeout)
        return True
