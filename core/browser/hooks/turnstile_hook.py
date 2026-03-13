import asyncio
from typing import Optional
from core.browser.hooks.base_hook import BaseHook, HookContext
from core.browser.security import TurnstileSolver

class TurnstileHook(BaseHook):
    def __init__(self) -> None:
        super().__init__()
        self._solver = TurnstileSolver()
        self._task: Optional[asyncio.Task] = None

    async def execute(self, ctx: HookContext) -> bool:
        async def _daemon():
            while True:
                try:
                    await self._solver.solve(ctx.page_context)
                    await asyncio.sleep(1)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.logger.debug(f"Turnstile check skipped: {e}")

        self._task = asyncio.create_task(_daemon())
        return True

    async def destroy(self, ctx: HookContext) -> None:
        if self._task is None:
            return

        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.debug(f"Turnstile daemon finished: {e}")
