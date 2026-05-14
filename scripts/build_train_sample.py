import sys
import signal
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.config.config_manager import ConfigManager
from core.logger.logger_manager import LoggerManager
from core.store.postgres.postgresql_manager import PostgreSQLManager
from core.services.league.league_service import get_league_service
from core.services.ml.training.train_sample import TrainSampleBuilder

logger = LoggerManager.get_instance().get_logger(__name__)

def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Build training samples')
    parser.add_argument('--config', '-c', type=str, default='configs/config.yml')
    parser.add_argument('--league_id', type=int, required=True)
    parser.add_argument('--min_season', type=int, required=True)
    parser.add_argument('--max_season', type=int, required=True)
    parser.add_argument('--sample_format', type=str, default='csv', choices=['csv', 'parquet'])
    parser.add_argument('--sample_path', type=str, default='artifacts/dataset/training')
    return parser.parse_args()

def signal_handler(signum, frame) -> None:
    logger.info(f"Received signal {signum}, shutting down...")
    PostgreSQLManager.get_instance().cleanup()
    sys.exit(0)

def main() -> None:
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    args = parse_arguments()
    ConfigManager.get_instance().load_config(args.config)

    logger_config = ConfigManager.get_instance().get_config("logger")
    LoggerManager.get_instance().setup(logger_config)

    PostgreSQLManager.get_instance().startup()

    get_league_service().load()

    try:
        TrainSampleBuilder(args.league_id, args.min_season, args.max_season, args.sample_path, args.sample_format).build()
    finally:
        PostgreSQLManager.get_instance().cleanup()

if __name__ == "__main__":
    main()
