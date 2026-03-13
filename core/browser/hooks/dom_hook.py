from typing import Optional
from core.browser.hooks.base_hook import BaseHook, HookContext
from core.browser.hooks.latch import SignalLatch
from core.browser.intercept_policy import InterceptType

class DomHook(BaseHook):
    def __init__(self) -> None:
        super().__init__()
        self._latch: Optional[SignalLatch] = None

    async def setup(self, ctx: HookContext) -> None:
        dom_rule = ctx.policy.find_rule(type=InterceptType.DOM)
        if dom_rule is None:
            return

        self._latch = SignalLatch()

        async def _dom_loaded_handler(_page) -> None:
            try:
                parsed_data = await dom_rule.receiver.process(
                    page_context=ctx.page_context,
                    url=ctx.target_url,
                    timeout=ctx.policy.timeout
                )

                if parsed_data is None:
                    return

                ctx.result_set.set(dom_rule.receiver.instance_id, parsed_data)
            except Exception as e:
                self.logger.error(f"Failed to process page content from {ctx.target_url}: {e}", exc_info=True)
            finally:
                self._latch.mark_completed()

        ctx.page_context.on("load", _dom_loaded_handler)

    async def execute(self, ctx: HookContext) -> bool:
        if self._latch is not None:
            await self._latch.wait(ctx.policy.timeout)
        return True
