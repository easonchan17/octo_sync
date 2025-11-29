
import signal
import argparse
from threading import Event
from core.server.web_server import WebServer
from core.browser.interceptor import Interceptor
from core.scheduler.task_executor import TaskExecutor
from core.config.config_manager import ConfigManager
from core.logger.logger_manager import LoggerManager
from core.store.postgres.postgresql_manager import PostgreSQLManager

logger = LoggerManager.get_instance().get_logger(__name__)
shutdown_event = Event()

def signal_handler(signum, frame) -> None:
    logger.info(f"Received signal {signum}, shutting down gracefully...")

    logger.info("🔧 Stopping web server...")
    WebServer.get_instance().stop()
    logger.info("✅ Web server stopped")

    logger.info("🔧 Stopping task manager...")
    TaskExecutor.get_instance().stop()
    logger.info("✅ Task manager stopped")

    logger.info("🔧 Stopping network interceptor...")
    Interceptor.get_instance().stop()
    logger.info("✅ Network interceptor stopped")

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
    config = ConfigManager.get_instance().get_config("logger")
    LoggerManager.get_instance().setup(config)
    logger.info("✅ Logger manager initialized")

    logger.info("🔧 Starting PostgreSQL manager...")
    PostgreSQLManager.get_instance().startup()
    logger.info("✅ PostgreSQL manager started")

    logger.info("🔧 Starting network interceptor...")
    Interceptor.get_instance().start()
    logger.info("✅ Network interceptor started")

    logger.info("🔧 Starting task manager...")
    TaskExecutor.get_instance().start()
    logger.info("✅ Task manager started")

    logger.info("🌐 Starting web server...")
    WebServer.get_instance().start()
    logger.info("✅ Web server started")

    shutdown_event.wait()

if __name__ == "__main__":
   run_app()