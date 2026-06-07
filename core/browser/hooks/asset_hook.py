from core.browser.hooks.base_hook import BaseHook, HookContext
from core.browser.intercept_strategy import InterceptType
from core.browser.intercept_result_set import FetchState


class AssetHook(BaseHook):
    async def execute(self, ctx: HookContext) -> bool:
        asset_rule = ctx.strategy.find_rule(type=InterceptType.ASSET)
        if asset_rule is None or asset_rule.receiver is None:
            return True

        if ctx.response is None:
            return False

        if ctx.response.status == 403:
            ctx.result_set.set(asset_rule.receiver.instance_id, FetchState.FORBIDDEN)
            return True

        parsed_data = await asset_rule.receiver.process(response=ctx.response)

        if parsed_data is not None:
            ctx.result_set.set(asset_rule.receiver.instance_id, parsed_data)
            self.logger.info(f"Asset captured from: {ctx.target_url}")

        return True
