
import os
import signal
import argparse
from pathlib import Path
from threading import Event
from dotenv import load_dotenv
from core.scheduler.worker import Worker
from core.server.web_server import WebServer
from core.browser.interceptor import Interceptor
from core.config.config_manager import ConfigManager
from core.logger.logger_manager import LoggerManager
from core.registry.workflows.cron import init_cron_jobs
from core.store.postgres.postgresql_manager import PostgreSQLManager
from core.scheduler.cron import Cron

logger = LoggerManager.get_instance().get_logger(__name__)
shutdown_event = Event()

def signal_handler(signum, frame) -> None:
    logger.info(f"Received signal {signum}, shutting down gracefully...")

    logger.info("🔧 Stopping cron...")
    Cron.get_instance().stop()
    logger.info("✅ Cron stopped")

    logger.info("🔧 Stopping web server...")
    WebServer.get_instance().stop()
    logger.info("✅ Web server stopped")

    logger.info("🔧 Stopping worker...")
    Worker.get_instance().stop()
    logger.info("✅ Worker stopped")

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

def load_env() -> None:
    env_path = Path(__file__).parent / '.env'
    if not env_path.exists():
        raise FileNotFoundError(f".env file not found at {env_path}")

    load_dotenv(dotenv_path=env_path)

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

    logger.info("🔧 Starting worker...")
    Worker.get_instance().start()
    logger.info("✅ Worker started")

    logger.info("🔧 Starting cron...")
    Cron.get_instance().start()
    logger.info("✅ Cron started")

    logger.info("🔧 Initializing cron jobs...")
    init_cron_jobs()
    logger.info("✅ Cron jobs initialized")

    logger.info("🌐 Starting web server...")
    WebServer.get_instance().start()
    logger.info("✅ Web server started")

    shutdown_event.wait()

if __name__ == "__main__":
    load_env()
    run_app()
