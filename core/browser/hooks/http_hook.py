from contextlib import suppress
from typing import Optional
from core.browser.hooks.base_hook import BaseHook, HookContext
from core.browser.hooks.latch import PatternLatch
from core.browser.intercept_strategy import InterceptType
from core.browser.intercept_result_set import FetchState

class HttpHook(BaseHook):
    def __init__(self) -> None:
        super().__init__()
        self._latch: Optional[PatternLatch] = None

    async def setup(self, ctx: HookContext) -> None:
        if not ctx.strategy.has_rules(InterceptType.HTTP):
            return

        if ctx.strategy.has_senders(InterceptType.HTTP):
            async def _http_request_handler(route, request) -> None:
                try:
                    rule = ctx.strategy.find_rule(InterceptType.HTTP, request.url)
                    if rule and rule.sender:
                        overrides = await rule.sender.process(request, ctx.query_params)

                        if overrides is not None:
                            await route.continue_(**overrides)
                            return
                except Exception as e:
                    self.logger.error(f"Failed to send request: {e}")

                try:
                    if ctx.strategy.debug:
                        self.logger.info(f"Continuing request without modification: {request.url}")
                    await route.fallback()
                except Exception as e:
                    is_main_doc = request.is_navigation_request() and request.resource_type == "document"
                    if is_main_doc:
                        with suppress(Exception):
                            await route.fallback()
                    else:
                        with suppress(Exception):
                            await route.abort("failed")

                    self.logger.error(f"Failed to continue request: {e}")

            await ctx.page_context.route("**/*", _http_request_handler)

        if ctx.strategy.has_receivers(InterceptType.HTTP):
            self._latch = PatternLatch(ctx.strategy.get_url_patterns(InterceptType.HTTP))

            async def _http_response_handler(response) -> None:
                http_rule = ctx.strategy.find_rule(
                    type=InterceptType.HTTP,
                    url=response.url
                )
                if http_rule is None or http_rule.receiver is None:
                    if ctx.strategy.debug:
                        self.logger.warning(f"No receiver found for HTTP rule: {response.url}")
                    return

                if not response.ok:
                    if response.status == 304:
                        ctx.result_set.set(http_rule.receiver.instance_id, FetchState.NOT_MODIFIED)
                    self._latch.mark_completed(http_rule.pattern)
                    return

                try:
                    parsed_data = await http_rule.receiver.process(response)
                    if parsed_data is None:
                        return

                    ctx.result_set.set(http_rule.receiver.instance_id, parsed_data)
                    self._latch.mark_completed(http_rule.pattern)
                except Exception as e:
                    self.logger.error(
                        f"Failed to process response from {response.url} "
                        f"{response.request.method} {http_rule.receiver}: {e}",
                        exc_info=True
                    )

            ctx.page_context.on("response", _http_response_handler)

    async def execute(self, ctx: HookContext) -> bool:
        if self._latch is not None:
            await self._latch.wait(ctx.strategy.timeout)
        return True
