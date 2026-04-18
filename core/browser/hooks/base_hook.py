from dataclasses import dataclass
from typing import Any
from core.logger.logger_manager import LoggerManager
from core.browser.intercept_strategy import InterceptStrategy
from core.browser.intercept_result_set import InterceptResultSet

@dataclass
class HookContext:
    page_context: Any
    target_url: str
    policy: InterceptStrategy
    result_set: InterceptResultSet

class BaseHook:
    def __init__(self) -> None:
        self.logger = LoggerManager.get_instance().get_logger(self.__class__.__name__)

    async def setup(self, ctx: HookContext) -> None:
        pass

    async def execute(self, ctx: HookContext) -> bool:
        return True

    async def destroy(self, ctx: HookContext) -> None:
        pass
