import sys
import signal
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

if Path('.').resolve() != Path(__file__).resolve().parents[1]:
    sys.exit(f"Must be run from project root: {Path(__file__).resolve().parents[1]}")

from core.config.config_manager import get_config_manager
from core.logger.logger_manager import get_logger_manager
from core.store.postgres.postgresql_manager import get_postgresql_manager
from core.services.league.league_service import get_league_service
from core.services.ml.training.train_sample import TrainSampleBuilder

logger = get_logger_manager().get_logger(__name__)

def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Build training samples')
    parser.add_argument('--config', '-c', type=str, default='configs/config.yml')
    parser.add_argument('--league_ids', type=int, nargs='+', required=True)
    parser.add_argument('--min_season', type=int, required=True)
    parser.add_argument('--max_season', type=int, required=True)
    parser.add_argument('--sample_format', type=str, default='csv', choices=['csv', 'parquet'])
    parser.add_argument('--sample_path', type=str, default='artifacts/dataset/training')
    return parser.parse_args()

def signal_handler(signum, frame) -> None:
    logger.info(f"Received signal {signum}, shutting down...")
    get_postgresql_manager().cleanup()
    sys.exit(0)

def main() -> None:
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    args = parse_arguments()
    get_config_manager().load_config(args.config)

    logger_config = get_config_manager().get_config("logger")
    get_logger_manager().setup(logger_config)

    get_postgresql_manager().startup()

    get_league_service().load()

    try:
        TrainSampleBuilder(args.league_ids, args.min_season, args.max_season, args.sample_path, args.sample_format).build()
    finally:
        get_postgresql_manager().cleanup()

if __name__ == "__main__":
    main()
