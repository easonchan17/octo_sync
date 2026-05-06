import threading
from functools import lru_cache
from typing import Optional, Dict
from concurrent.futures import Future
from core.logger.logger_manager import LoggerManager
from core.browser.interceptor import Interceptor
from core.browser.intercept_strategy import InterceptStrategy

class InterceptorManager:
    def __init__(self) -> None:
        self.logger = LoggerManager.get_instance().get_logger(self.__class__.__name__)
        self._lock = threading.Lock()
        self.interceptors: Dict[str, Interceptor] = {}

    def get(self, site_name: str) -> Optional[Interceptor]:
        with self._lock:
            interceptor = self.interceptors.get(site_name)
            if not interceptor:
                self.logger.error(f"No interceptor found for site: {site_name}")
                return None

            return interceptor

    def start(self, site_name: str, request_interval: float, launch_options: Dict, viewport: Dict, addons: Optional[list] = None) -> None:
        with self._lock:
            if site_name in self.interceptors:
                self.logger.warning(f"Interceptor for site {site_name} is already running")
                return

            interceptor = Interceptor(
                request_interval=request_interval,
                launch_options=launch_options,
                viewport=viewport,
                addons=addons
            )
            interceptor.start()
            self.interceptors[site_name] = interceptor
            self.logger.info(f"Started interceptor for site: {site_name}")

    def stop(self, site_name: str) -> None:
        with self._lock:
            interceptor = self.interceptors.get(site_name)
            if not interceptor:
                self.logger.warning(f"No interceptor found for site: {site_name}")
                return

            interceptor.stop()
            self.interceptors.pop(site_name, None)
            self.logger.info(f"Stopped interceptor for site: {site_name}")


@lru_cache(maxsize=None)
def get_interceptor_manager() -> InterceptorManager:
    return InterceptorManager()

interceptor_manager = get_interceptor_manager()