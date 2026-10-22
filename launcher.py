import os, sys, signal, argparse, warnings
from importlib.resources import files
from dotenv import load_dotenv
from sqlalchemy import text
from typing import Callable, List, Optional, Tuple, final
from urllib3.exceptions import InsecureRequestWarning
from threading import Event, enumerate as enumerate_threads
from core.config.config_manager import get_config_manager
from core.config.env_manager import get_env_manager
from core.logger.logger_manager import get_logger_manager
from core.store.postgres.postgresql_manager import get_postgresql_manager
from core.services.league.league_service import get_league_service
from core.services.name_i18n_service import get_name_i18n_service
from core.server.http.web_server import get_web_server
from core.scheduler.task_executor import get_task_executor
from core.scheduler.poll_manager import get_poll_manager
from core.browser.interceptor import get_interceptor
from abc import ABC

warnings.filterwarnings("ignore", category=InsecureRequestWarning)


class BaseLauncher(ABC):
    def __init__(self, config: str) -> None:
        self.logger = get_logger_manager().get_logger(self.__class__.__name__)
        self.config = config
        self.shutdown_event = Event()
        self.services: List[Tuple[str, Callable[[], None], Optional[Callable[[], None]]]] = []

    @final
    def setup(self) -> None:
        load_dotenv()

        self.logger.info(f"Loading configuration file: {self.config}")
        get_config_manager().load_config(self.config)

        self.logger.info(f"Initializing logger manager...")
        get_logger_manager().setup(get_config_manager().get_config("logger"))
        self.logger.info("Logger manager initialized")

        self._register_services()

    def run(self) -> None:
        signal.signal(signal.SIGINT, self._on_shutdown)
        signal.signal(signal.SIGTERM, self._on_shutdown)

        for name, start, _ in self.services:
            self.logger.info(f"Starting {name}...")
            start()
            self.logger.info(f"{name} started")

        self.shutdown_event.wait()
        for thread in enumerate_threads():
            self.logger.info(f"Still running thread: {thread.name} daemon={thread.daemon}")

        os._exit(0)

    def _on_shutdown(self, signum, frame) -> None:
        if self.shutdown_event.is_set():
            return

        self.logger.info(f"Received signal {signum}, shutting down gracefully...")
        for name, _, stop in reversed(self.services):
            if stop is None:
                continue

            self.logger.info(f"Stopping {name}...")
            stop()
            self.logger.info(f"{name} stopped")

        self.shutdown_event.set()

    def _register_services(self) -> None:
        postgresql_manager = get_postgresql_manager()
        league_service     = get_league_service()

        self._add_service("PostgreSQLManager", postgresql_manager.startup, postgresql_manager.cleanup)
        self._add_service("SeedData",          self._seed_reference_data, None)
        self._add_service("LeagueService",     league_service.load,        None)

    def _add_service(self, name: str, start: Callable[[], None], stop: Optional[Callable[[], None]]) -> None:
        self.services.append((name, start, stop))

    def _seed_reference_data(self) -> None:
        sql = files("core.store.postgres").joinpath("seeds", "leagues.sql").read_text(encoding="utf-8")

        try:
            with get_postgresql_manager().get_session() as session:
                session.execute(text(sql))
        except Exception:
            self.logger.exception("Failed to initialize league data")
            raise

        self.logger.info("League data initialized")


class CrawlerLauncher(BaseLauncher):
    def _register_services(self) -> None:
        super()._register_services()

        task_executor      = get_task_executor()
        interceptor        = get_interceptor()
        poll_manager       = get_poll_manager()
        env                = get_env_manager()

        self._add_service("TaskExecutor",      task_executor.start,        task_executor.stop)
        self._add_service("Interceptor",       interceptor.start,          interceptor.stop)
        self._add_service("PollManager",       lambda: poll_manager.start(include=env.TASK_INCLUDE, exclude=env.TASK_EXCLUDE), poll_manager.stop)


class ApiLauncher(BaseLauncher):
    def _register_services(self) -> None:
        super()._register_services()

        name_i18n_service  = get_name_i18n_service()
        web_server         = get_web_server()

        self._add_service("NameI18nService",   name_i18n_service.load,     None)
        self._add_service("WebServer",         web_server.start,           web_server.stop)


def main() -> None:
    if sys.version_info < (3, 11):
        sys.exit("Python 3.14 or higher is required")

    base_dir = os.path.dirname(os.path.abspath(__file__))
    if os.path.abspath('.') != base_dir:
        sys.exit(f"Must be run from project root: {base_dir}")

    launchers = {
        'crawler': CrawlerLauncher,
        'api': ApiLauncher,
    }
    parser = argparse.ArgumentParser(description='Octopus Launcher')
    parser.add_argument(
        'role',
        choices=sorted(launchers.keys()),
    )
    parser.add_argument(
        '--config', '-c',
        type=str,
        default='configs/config.yml',
        help='Configuration file path (default: configs/config.yml)'
    )
    args = parser.parse_args()

    launcher = launchers[args.role](config=args.config)
    launcher.setup()
    launcher.run()


if __name__ == "__main__":
    main()
