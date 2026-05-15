from core.browser.hooks.base_hook import BaseHook, HookContext
from core.browser.intercept_strategy import InterceptType

class DomHook(BaseHook):
    async def execute(self, ctx: HookContext) -> bool:
        dom_rule = ctx.strategy.find_rule(type=InterceptType.DOM)
        if dom_rule is None:
            return True

        if dom_rule.wait_selector:
            await ctx.page_context.wait_for_selector(
                dom_rule.wait_selector,
                state='attached',
                timeout=ctx.strategy.timeout * 1000
            )

        parsed_data = await dom_rule.receiver.process(page_context=ctx.page_context)

        if parsed_data is not None:
            ctx.result_set.set(dom_rule.receiver.instance_id, parsed_data)
            self.logger.info(f"Data captured from: {ctx.target_url}")

        return True
