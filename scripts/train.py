import sys
import signal
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.config.config_manager import ConfigManager
from core.logger.logger_manager import LoggerManager
from core.store.postgres.postgresql_manager import PostgreSQLManager
from core.services.ml.training.trainer import WinballTrainer

logger = LoggerManager.get_instance().get_logger(__name__)

def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Train winball model')
    parser.add_argument('--config',                 '-c', type=str,   default='configs/config.yml')
    parser.add_argument('--dataset_name',                  type=str,   required=True)
    parser.add_argument('--test_set_size',                 type=float, default=0.2)
    parser.add_argument('--eval_set_size',                 type=float, default=0.1)
    parser.add_argument('--balanced',                      action='store_true')
    parser.add_argument('--early_stopping_rounds',         type=int,   default=150)
    parser.add_argument('--n_iter',                        type=int,   default=200)
    parser.add_argument('--scoring',                       type=str,   default='accuracy')
    return parser.parse_args()

def build_payload(args: argparse.Namespace) -> dict:
    return {
        "dataset_name": args.dataset_name,
        "objective": {
            "test_set_size": args.test_set_size,
            "eval_set_size": args.eval_set_size,
            "balanced":      args.balanced,
        },
        "model": {
            "params": {
                "early_stopping_rounds": args.early_stopping_rounds,
            }
        },
        "optimizer": {
            "params": {
                "n_iter":   args.n_iter,
                "scoring":  args.scoring,
            }
        },
    }

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

    try:
        WinballTrainer(build_payload(args)).train()
    finally:
        PostgreSQLManager.get_instance().cleanup()

if __name__ == "__main__":
    main()
