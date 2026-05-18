import os, sys, signal, argparse
from threading import Event, enumerate
from core.server.http.web_server import get_web_server
from core.config.config_manager import get_config_manager
from core.logger.logger_manager import get_logger_manager
from core.scheduler.task_executor import get_task_executor
from core.scheduler.cron_manager import get_cron_manager
from core.scheduler.poll_manager import get_poll_manager
from core.store.postgres.postgresql_manager import get_postgresql_manager
from core.services.league.league_service import get_league_service
from core.browser.interceptor_manager import get_interceptor_manager
from core.config.env_manager import get_env_manager
from core.types.enums import SiteName

import warnings
from urllib3.exceptions import InsecureRequestWarning
warnings.filterwarnings("ignore", category=InsecureRequestWarning)


if sys.version_info < (3, 11):
    sys.exit("Python 3.14 or higher is required")


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if os.path.abspath('.') != BASE_DIR:
    sys.exit(f"Must be run from project root: {BASE_DIR}")

logger = get_logger_manager().get_logger(__name__)
shutdown_event = Event()

def signal_handler(signum, frame) -> None:
    logger.info(f"Received signal {signum}, shutting down gracefully...")

    logger.info("🔧 Stopping web server...")
    get_web_server().stop()
    logger.info("✅ Web server stopped")

    logger.info("🔧 Stopping cron...")
    get_cron_manager().stop()
    logger.info("✅ Cron stopped")


    if not get_env_manager().is_ml:
        logger.info("🔧 Stopping interceptor manager...")
        get_interceptor_manager().stop()
        logger.info("✅ Interceptor manager stopped")

    logger.info("🔧 Stopping task executor...")
    get_task_executor().stop()
    logger.info("✅ TaskExecutor stopped")

    logger.info("🔧 Cleaning up PostgreSQL manager...")
    get_postgresql_manager().cleanup()
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
    get_config_manager().load_config(args.config)

    logger.info(f"🔧 Initializing logger manager...")
    logger_config = get_config_manager().get_config("logger")
    get_logger_manager().setup(logger_config)
    logger.info("✅ Logger manager initialized")

    logger.info("🔧 Starting PostgreSQL manager...")
    get_postgresql_manager().startup()
    logger.info("✅ PostgreSQL manager started")

    if not get_env_manager().is_ml:
        browser_config = get_config_manager().get_config("browser")
        launch_options = browser_config["launch_options"]
        viewport = browser_config['viewport']
        addons = [os.path.join(BASE_DIR, p) for p in browser_config.get("addons", [])]
        request_interval = browser_config["request_interval"]
        page_pool_size = browser_config["page_pool_size"]
        sys_mem_threshold = browser_config["sys_mem_threshold"]
        failure_threshold = browser_config["failure_threshold"]

        logger.info("🔧 Starting network interceptor...")
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
        logger.info("✅ Network interceptor started")

    logger.info("🔧 Starting task executor...")
    get_task_executor().start()
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
    get_web_server().start()
    logger.info("✅ Web server started")

    shutdown_event.wait()

    for thread in enumerate():
        logger.info(f"Still running thread: {thread.name} daemon={thread.daemon}")

    os._exit(0)

if __name__ == "__main__":
    run_app()
