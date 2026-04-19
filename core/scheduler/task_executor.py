from queue import Queue, Empty
from core.utils.thread import Thread
from core.utils.singleton import Singleton
from core.config.config_manager import ConfigManager
from concurrent.futures import ThreadPoolExecutor
from .base_task import BaseTask

class TaskExecutor(Thread, Singleton):
    def __init__(self) -> None:
        super().__init__()
        self.task_queue = Queue()

    def submit(self, task: BaseTask) -> str:
        self.task_queue.put(task)
        return task.id

    def _run(self) -> None:
        max_workers = ConfigManager.get_instance().get_config("task_thread_pool.max_workers", 10)
        thread_pool = ThreadPoolExecutor(max_workers=max_workers)

        tasks = []
        while not self.stop_event.is_set():
            try:
                task = self.task_queue.get(timeout=1)
            except Empty:
                continue

            try:
                if task is not None:
                    thread_pool.submit(task.execute)
                    tasks.append(task)
                    self.logger.info(f"TaskExecutor executing task: {task.id} {task.name}")
            except Exception as e:
                self.logger.error(f"Error in TaskExecutor thread: {e}")
            finally:
                self.task_queue.task_done()

        for task in tasks:
            task.cancel()

        thread_pool.shutdown(wait=True, cancel_futures=True)
