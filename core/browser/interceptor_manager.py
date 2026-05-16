import threading
from functools import cache
from typing import Optional, Dict
from concurrent.futures import Future
from core.logger.logger_manager import LoggerManager
from core.browser.interceptor import Interceptor
from core.browser.intercept_strategy import InterceptStrategy

class InterceptorManager:
    def __init__(self) -> None:
        self.logger = LoggerManager.get_instance().get_logger(self.__class__.__name__)
        self._lock = threading.Lock()
        self._interceptor: Optional[Interceptor] = None

    def get(self, site_name: Optional[str] = None) -> Optional[Interceptor]:
        with self._lock:
            if not self._interceptor:
                self.logger.error("Interceptor is not started")
                return None

            return self._interceptor

    def start(self, request_interval: float, launch_options: Dict, viewport: Dict, addons: Optional[list] = None) -> None:
        with self._lock:
            if self._interceptor:
                self.logger.warning("Interceptor is already running")
                return

            interceptor = Interceptor(
                request_interval=request_interval,
                launch_options=launch_options,
                viewport=viewport,
                addons=addons
            )
            interceptor.start()
            self._interceptor = interceptor
            self.logger.info("Started interceptor")

    def stop(self) -> None:
        with self._lock:
            if not self._interceptor:
                self.logger.warning("Interceptor is not running")
                return

            self._interceptor.stop()
            self._interceptor = None
            self.logger.info("Stopped interceptor")


@cache
def get_interceptor_manager() -> InterceptorManager:
    return InterceptorManager()
