from typing import Optional
from core.browser.hooks.latch import SignalLatch
from core.browser.hooks.base_hook import BaseHook, HookContext
from core.browser.intercept_strategy import InterceptType

class DomHook(BaseHook):
    def __init__(self) -> None:
        super().__init__()
        self._latch: Optional[SignalLatch] = None

    async def setup(self, ctx: HookContext) -> None:
        dom_rule = ctx.strategy.find_rule(type=InterceptType.DOM)
        if dom_rule is None:
            return

        self._latch = SignalLatch()

        async def _dom_loaded_handler(_page) -> None:
            try:
                if dom_rule.wait_selector:
                    await ctx.page_context.wait_for_selector(
                        dom_rule.wait_selector,
                        state='attached',
                        timeout=ctx.strategy.timeout * 1000
                    )

                parsed_data = await dom_rule.receiver.process(
                    page_context=ctx.page_context,
                    url=ctx.target_url,
                    timeout=ctx.strategy.timeout
                )

                if parsed_data is None:
                    return

                ctx.result_set.set(dom_rule.receiver.instance_id, parsed_data)
                self.logger.info(f"Data captured from: {ctx.target_url}")
            except Exception as e:
                self.logger.error(f"Failed to process page content from {ctx.target_url}: {e}", exc_info=True)
            finally:
                self._latch.mark_completed()

        ctx.page_context.once("domcontentloaded", _dom_loaded_handler)

    async def execute(self, ctx: HookContext) -> bool:
        if self._latch is not None:
            await self._latch.wait(ctx.strategy.timeout)
        return True
