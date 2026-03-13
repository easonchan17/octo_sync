from typing import Optional, Any
from core.browser.hooks.base_hook import BaseHook, HookContext
from core.browser.hooks.latch import SignalLatch
from core.browser.intercept_policy import InterceptType

class JsHook(BaseHook):
    def __init__(self) -> None:
        super().__init__()
        self._latch: Optional[SignalLatch] = None

    async def setup(self, ctx: HookContext) -> None:
        js_rule = ctx.policy.find_rule(type=InterceptType.JS)
        if js_rule is None:
            return

        self._latch = SignalLatch()

        async def _trace_log_handler(payload: Any) -> None:
            try:
                if js_rule.receiver:
                    payload = await js_rule.receiver.process(payload)

                ctx.result_set.set(js_rule.receiver.instance_id, payload)
            except Exception as e:
                self.logger.error(f"Failed to set js payload: {e}", exc_info=True)
            finally:
                self._latch.mark_completed()

        if js_rule.hook_script:
            await ctx.page_context.expose_function("traceLog", _trace_log_handler)
            await ctx.page_context.add_init_script(js_rule.hook_script)

    async def execute(self, ctx: HookContext) -> bool:
        if self._latch is not None:
            await self._latch.wait(ctx.policy.timeout)
        return True
