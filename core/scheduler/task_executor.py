from queue import Queue, Empty
from concurrent.futures import ThreadPoolExecutor
from core.utils.thread import Thread
from core.utils.singleton import Singleton
from core.config.config_manager import ConfigManager
from .tasks.base_task import BaseTask

class TaskExecutor(Thread, Singleton):
    def __init__(self) -> None:
        super().__init__()
        self.task_queue = Queue()

    def submit_task(self, task: BaseTask) -> str:
        self.task_queue.put(task)
        return task.id

    def _run(self) -> None:
        max_workers = ConfigManager.get_instance().get_config("thread_pool.max_workers", 10)
        thread_pool = ThreadPoolExecutor(max_workers=max_workers)

        tasks = []
        while not self.stop_event.is_set():
            try:
                task = self.task_queue.get(timeout=1)
            except Empty:
                continue

            try:
                if task is not None:
                    if task.is_async:
                        thread_pool.submit(task.execute)
                        tasks.append(task)
                        self.logger.info(f"Execute async task: {task.id} {task.name}")
                    else:
                        task.execute()
                        self.logger.info(f"Execute sync task: {task.id} {task.name}")
            except Exception as e:
                self.logger.error(f"Error in TaskManager thread: {e}")
            finally:
                self.task_queue.task_done()

        for task in tasks:
            task.cancel()
        thread_pool.shutdown(wait=True)
