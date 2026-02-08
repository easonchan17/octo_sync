import threading, uuid
from typing import Optional
from abc import ABC, abstractmethod
from core.logger.logger_manager import LoggerManager

class Thread(ABC):
    def __init__(self, name: str = None) -> None:
        super().__init__()
        self.logger = LoggerManager.get_instance().get_logger(self.__class__.__name__)
        self.name = name or self.__class__.__name__
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        self.thread = None
        self.id = str(uuid.uuid4())

    def start(self, daemon: bool = False) -> None:
        with self.lock:
            if self.thread is not None:
                self.logger.warning(f"{self.name} is already running")
                return

            self.thread = threading.Thread(target=self._run, name=self.name, daemon=daemon)
            self.thread.start()
            self.logger.debug(f"{self.name} started")

    def stop(self, timeout: Optional[float] = 60.0) -> None:
        with self.lock:
            if self.thread is None:
                self.logger.warning(f"{self.name} is not running")
                return

            self.logger.debug(f"Stopping {self.name}...")
            self.stop_event.set()
            self.thread.join(timeout=timeout)
            if self.thread.is_alive():
                self.logger.warning(f"{self.name} did not stop within {timeout} seconds")
            else:
                self.logger.debug(f"{self.name} stopped successfully")

            self.thread = None
            self.stop_event.clear()

    def join(self) -> None:
        if self.thread is None:
            self.logger.warning(f"{self.name} is not running")
            return

        self.thread.join()
        self.logger.debug(f"{self.name} joined")

    @abstractmethod
    def _run(self) -> None:
        pass