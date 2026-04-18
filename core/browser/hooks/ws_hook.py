from playwright.async_api import WebSocket
from core.browser.hooks.base_hook import BaseHook, HookContext
from core.browser.intercept_strategy import InterceptType

class WsHook(BaseHook):
    async def setup(self, ctx: HookContext) -> None:
        if not ctx.policy.has_rules(InterceptType.WS):
            return

        async def _ws_connect_handler(ws: WebSocket):
            ws_rule = ctx.policy.find_rule(
                type=InterceptType.WS,
                url=ws.url
            )
            if not ws_rule or not ws_rule.receiver:
                return

            async def _framereceived_handler(frame):
                try:
                    await ws_rule.receiver.process(frame)
                except Exception as e:
                    self.logger.error(f"Failed to process ws frame from {ws.url}: {e}")

            async def _close_handler(code):
                self.logger.info(f"ws closed: {ws.url}, code {code}")

            async def _error_handler(error):
                self.logger.error(f"ws error: {ws.url} {error}")

            self.logger.info(f"ws opened: {ws.url}")

            ws.on("close", _close_handler)
            ws.on("error", _error_handler)
            ws.on("framereceived", _framereceived_handler)

        ctx.page_context.on("websocket", _ws_connect_handler)

    async def execute(self, ctx: HookContext) -> bool:
        if ctx.policy.has_rules(InterceptType.WS):
            ctx.page_context.detach()
        return True
