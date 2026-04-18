import re
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
        self._js_inject_handler = None

    async def setup(self, ctx: HookContext) -> None:
        js_rule = ctx.policy.find_rule(type=InterceptType.JS)
        if js_rule is None or not js_rule.hook_script:
            return

        self._latch = SignalLatch()

        async def _trace_handler(route, request) -> None:
            try:
                post_data = request.post_data
                if not post_data:
                    self.logger.warning(f"Received trace request with empty body from: {request.url}")
                    return

                json_data = json.loads(post_data)
                if js_rule.on_trace:
                    json_data =  await js_rule.on_trace(ctx, json_data)
                    if json_data is None:
                        self.logger.info(f"Trace data discarded by on_trace handler for: {request.url}")
                        return

                # self.logger.info(f"Received trace data from: {request.url} with payload:\n{json.dumps(json_data, indent=2, ensure_ascii=False)}")
                ctx.result_set.set(1, json_data)
                self._latch.mark_completed()

                self.logger.info(f"Trace data captured from: {request.url}")
            except Exception as e:
                self.logger.error(f"Failed to process trace data from: {request.url}: {e}", exc_info=True)
            finally:
                try:
                    await route.fulfill(status=200, body="ok")
                except Exception:
                    pass

        async def _js_inject_handler(route, request) -> None:
            response = None
            fulfilled = False

            try:
                if request.resource_type != "document":
                    return

                response = await route.fetch(max_redirects=0)
                if response.status in (301, 302, 303, 307, 308):
                    location = response.headers.get('location')
                    if location is None:
                        self.logger.error(f"Redirect response without location header for: {request.url}")
                        return

                    response = await ctx.page_context.request.get(location)

                body, headers = await self._patch_response(response, js_rule.hook_script)
                await route.fulfill(response=response, body=body, headers=headers)
                fulfilled = True

                self.logger.info(f"Injected hook script into: {request.url}")
            except Exception as e:
                self.logger.error(f"Failed to inject hook script into: {request.url}: {e}", exc_info=True)
            finally:
                try:
                    if response is None:
                        await route.fallback()
                    elif not fulfilled:
                        await route.fulfill(response=response)
                except Exception:
                    pass

        self._trace_handler = _trace_handler
        self._js_inject_handler = _js_inject_handler
        await ctx.page_context.route(self.TRACE_ROUTE_PATTERN, _trace_handler)
        await ctx.page_context.route("**/*", _js_inject_handler)

    async def destroy(self, ctx: HookContext) -> None:
        with suppress(Exception):
            await ctx.page_context.unroute(self.TRACE_ROUTE_PATTERN, self._trace_handler)
        with suppress(Exception):
            await ctx.page_context.unroute("**/*", self._js_inject_handler)

    async def _patch_response(self, response, hook_script: str) -> tuple[str, dict]:
        script_tag = f"<script>{hook_script}</script>"
        body = await response.text()
        patched_body, count = re.subn(
            r'(<head[^>]*>)',
            lambda m: m.group(1) + script_tag,
            body,
            count=1,
            flags=re.IGNORECASE
        )
        if count == 0:
            patched_body = script_tag + body

        csp_keys = {'content-security-policy', 'content-security-policy-report-only'}
        clean_headers = {k: v for k, v in response.headers.items() if k not in csp_keys}
        return patched_body, clean_headers

    async def execute(self, ctx: HookContext) -> bool:
        if self._latch is None:
            return True

        await self._latch.wait(ctx.policy.timeout)
        return True
