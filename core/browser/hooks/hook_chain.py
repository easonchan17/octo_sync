from contextlib import suppress
from core.browser.hooks.base_hook import BaseHook, HookContext


class HookChain:
    def __init__(self, hooks: list[BaseHook]) -> None:
        self._hooks = hooks

    async def setup(self, ctx: HookContext) -> None:
        for hook in self._hooks:
            await hook.setup(ctx)

    async def execute(self, ctx: HookContext) -> bool:
        for hook in self._hooks:
            if not await hook.execute(ctx):
                return False
        return True

    async def destroy(self, ctx: HookContext) -> None:
        for hook in self._hooks:
            with suppress(Exception):
                await hook.destroy(ctx)

        with suppress(Exception):
            await ctx.page_context.unroute_all(behavior='ignoreErrors')
