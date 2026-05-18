import os, sys, signal, argparse
from abc import ABC, abstractmethod
from threading import Event, enumerate as enumerate_threads
from core.config.config_manager import get_config_manager
from core.logger.logger_manager import get_logger_manager
from core.store.postgres.postgresql_manager import get_postgresql_manager
from core.services.league.league_service import get_league_service
from core.server.http.web_server import get_web_server
from core.scheduler.task_executor import get_task_executor
from core.scheduler.cron_manager import get_cron_manager
from core.scheduler.poll_manager import get_poll_manager
from core.browser.interceptor_manager import get_interceptor_manager
from core.types.enums import SiteName

import warnings
from urllib3.exceptions import InsecureRequestWarning
warnings.filterwarnings("ignore", category=InsecureRequestWarning)


if sys.version_info < (3, 11):
    sys.exit("Python 3.14 or higher is required")


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if os.path.abspath('.') != BASE_DIR:
    sys.exit(f"Must be run from project root: {BASE_DIR}")


class BaseLauncher(ABC):
    def __init__(self, config: str) -> None:
        self.logger = get_logger_manager().get_logger(self.__class__.__name__)
        self.config = config
        self.shutdown_event = Event()

    def run(self) -> None:
        signal.signal(signal.SIGINT, self._on_shutdown)
        signal.signal(signal.SIGTERM, self._on_shutdown)

        self.logger.info(f"🔧 Loading configuration file: {self.config}")
        get_config_manager().load_config(self.config)

        self.logger.info(f"🔧 Initializing logger manager...")
        get_logger_manager().setup(get_config_manager().get_config("logger"))
        self.logger.info("✅ Logger manager initialized")

        self.logger.info("🔧 Starting PostgreSQL manager...")
        get_postgresql_manager().startup()
        self.logger.info("✅ PostgreSQL manager started")

        self.logger.info("🔧 Loading league service...")
        get_league_service().load()
        self.logger.info("✅ League service loaded")

        self._start_services()

        self.shutdown_event.wait()
        for thread in enumerate_threads():
            self.logger.info(f"Still running thread: {thread.name} daemon={thread.daemon}")

        os._exit(0)

    def _on_shutdown(self, signum, frame) -> None:
        self.logger.info(f"Received signal {signum}, shutting down gracefully...")
        self._stop_services()

        self.logger.info("🔧 Cleaning up PostgreSQL manager...")
        get_postgresql_manager().cleanup()
        self.logger.info("✅ PostgreSQL manager cleaned up")

        self.shutdown_event.set()

    @abstractmethod
    def _start_services(self) -> None: ...

    @abstractmethod
    def _stop_services(self) -> None: ...


class CrawlerLauncher(BaseLauncher):
    def _start_services(self) -> None:
        browser_config = get_config_manager().get_config("browser")
        launch_options = browser_config["launch_options"]
        viewport = browser_config['viewport']
        addons = [os.path.join(BASE_DIR, p) for p in browser_config.get("addons", [])]
        request_interval = browser_config["request_interval"]
        page_pool_size = browser_config["page_pool_size"]
        sys_mem_threshold = browser_config["sys_mem_threshold"]
        failure_threshold = browser_config["failure_threshold"]

        self.logger.info("🔧 Starting network interceptor...")
        get_interceptor_manager().start(
            sites=[SiteName.FOTMOB.value, SiteName.ODDSPORTAL.value],
            request_interval=request_interval,
            launch_options=launch_options,
            viewport=viewport,
            page_pool_size=page_pool_size,
            sys_mem_threshold=sys_mem_threshold,
            failure_threshold=failure_threshold,
            addons=addons
        )
        self.logger.info("✅ Network interceptor started")

        self.logger.info("🔧 Starting task executor...")
        get_task_executor().start()
        self.logger.info("✅ TaskExecutor started")

        self.logger.info("🔧 Starting cron...")
        get_cron_manager().start()
        self.logger.info("✅ Cron started")

        self.logger.info("🔧 Starting poll manager...")
        get_poll_manager().start()
        self.logger.info("✅ Poll manager started")

    def _stop_services(self) -> None:
        self.logger.info("🔧 Stopping cron...")
        get_cron_manager().stop()
        self.logger.info("✅ Cron stopped")

        self.logger.info("🔧 Stopping interceptor manager...")
        get_interceptor_manager().stop()
        self.logger.info("✅ Interceptor manager stopped")

        self.logger.info("🔧 Stopping task executor...")
        get_task_executor().stop()
        self.logger.info("✅ TaskExecutor stopped")


class ApiLauncher(BaseLauncher):
    def _start_services(self) -> None:
        self.logger.info("🌐 Starting web server...")
        get_web_server().start()
        self.logger.info("✅ Web server started")

    def _stop_services(self) -> None:
        self.logger.info("🔧 Stopping web server...")
        get_web_server().stop()
        self.logger.info("✅ Web server stopped")


class UnifiedLauncher(CrawlerLauncher, ApiLauncher):
    def _start_services(self) -> None:
        CrawlerLauncher._start_services(self)
        ApiLauncher._start_services(self)

    def _stop_services(self) -> None:
        ApiLauncher._stop_services(self)
        CrawlerLauncher._stop_services(self)


def main() -> None:
    launchers = {
        'crawler': CrawlerLauncher,
        'api': ApiLauncher,
        'unified': UnifiedLauncher,
    }
    parser = argparse.ArgumentParser(description='Octopus Launcher')
    parser.add_argument(
        'role',
        nargs='?',
        choices=sorted(launchers.keys()),
        default='unified',
    )
    parser.add_argument(
        '--config', '-c',
        type=str,
        default='configs/config.yml',
        help='Configuration file path (default: configs/config.yml)'
    )
    args = parser.parse_args()
    launchers[args.role](config=args.config).run()


if __name__ == "__main__":
    main()
