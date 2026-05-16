import os, sys, signal, argparse
from threading import Event, enumerate
from core.server.http.web_server import WebServer
from core.config.config_manager import ConfigManager
from core.logger.logger_manager import LoggerManager
from core.scheduler.task_executor import TaskExecutor
from core.scheduler.cron_manager import get_cron_manager
from core.scheduler.poll_manager import get_poll_manager
from core.store.postgres.postgresql_manager import PostgreSQLManager
from core.services.league.league_service import get_league_service
from core.browser.interceptor_manager import get_interceptor_manager
from core.config.env_manager import get_env_manager

import warnings
from urllib3.exceptions import InsecureRequestWarning
warnings.filterwarnings("ignore", category=InsecureRequestWarning)


if sys.version_info < (3, 11):
    sys.exit("Python 3.14 or higher is required")


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if os.path.abspath('.') != BASE_DIR:
    sys.exit(f"Must be run from project root: {BASE_DIR}")

logger = LoggerManager.get_instance().get_logger(__name__)
shutdown_event = Event()

def signal_handler(signum, frame) -> None:
    logger.info(f"Received signal {signum}, shutting down gracefully...")

    logger.info("🔧 Stopping web server...")
    WebServer.get_instance().stop()
    logger.info("✅ Web server stopped")

    logger.info("🔧 Stopping cron...")
    get_cron_manager().stop()
    logger.info("✅ Cron stopped")


    logger.info("🔧 Stopping task executor...")
    TaskExecutor.get_instance().stop()
    logger.info("✅ TaskExecutor stopped")

    if not get_env_manager().is_ml:
        logger.info("🔧 Stopping interceptor manager...")
        get_interceptor_manager().stop()
        logger.info("✅ Interceptor manager stopped")

    logger.info("🔧 Cleaning up PostgreSQL manager...")
    PostgreSQLManager.get_instance().cleanup()
    logger.info("✅ PostgreSQL manager cleaned up")

    logger.info("🔧 Shutting down gracefully...")
    shutdown_event.set()

def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Web Crawler System')
    parser.add_argument(
        '--config',
        '-c',
        type=str,
        default='configs/config.yml',
        help='Configuration file path (default: configs/config.yml)'
    )
    return parser.parse_args()

def run_app() -> None:
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    args = parse_arguments()

    logger.info(f"🔧 Loading configuration file: {args.config}")
    ConfigManager.get_instance().load_config(args.config)

    logger.info(f"🔧 Initializing logger manager...")
    logger_config = ConfigManager.get_instance().get_config("logger")
    LoggerManager.get_instance().setup(logger_config)
    logger.info("✅ Logger manager initialized")

    logger.info("🔧 Starting PostgreSQL manager...")
    PostgreSQLManager.get_instance().startup()
    logger.info("✅ PostgreSQL manager started")

    if not get_env_manager().is_ml:
        browser_config = ConfigManager.get_instance().get_config("browser")
        launch_options = browser_config["launch_options"]
        viewport = browser_config['viewport']
        addons = [os.path.join(BASE_DIR, p) for p in browser_config.get("addons", [])]

        logger.info("🔧 Starting network interceptor...")
        get_interceptor_manager().start(
            request_interval=browser_config.get("request_interval", 20.0),
            launch_options=launch_options,
            viewport=viewport,
            addons=addons
        )
        logger.info("✅ Network interceptor started")

    logger.info("🔧 Starting task executor...")
    TaskExecutor.get_instance().start()
    logger.info("✅ TaskExecutor started")

    logger.info("🔧 Starting cron...")
    get_cron_manager().start()
    logger.info("✅ Cron started")

    logger.info("🔧 Loading league service...")
    get_league_service().load()
    logger.info("✅ League service loaded")

    logger.info("🔧 Starting poll manager...")
    get_poll_manager().start()
    logger.info("✅ Poll manager started")

    logger.info("🌐 Starting web server...")
    WebServer.get_instance().start()
    logger.info("✅ Web server started")

    shutdown_event.wait()

    for thread in enumerate():
        logger.info(f"Still running thread: {thread.name} daemon={thread.daemon}")

    os._exit(0)

if __name__ == "__main__":
    run_app()
