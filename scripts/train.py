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
from core.services.ml.training.trainer import WinballTrainer

logger = get_logger_manager().get_logger(__name__)

def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Train winball model')
    parser.add_argument('--config',                 '-c', type=str, default='configs/config.yml')
    parser.add_argument('--dataset_name',                  type=str, required=True)
    parser.add_argument('--test_set_size',                 type=float,                        help='e.g. 0.2 (20%% held-out test set)')
    parser.add_argument('--eval_set_size',                 type=float,                        help='e.g. 0.1 (10%% of train for early stopping)')
    parser.add_argument('--calibration_set_size',          type=float,                        help='e.g. 0.1 (10%% for isotonic calibration)')
    parser.add_argument('--balanced',                      action='store_true',               help='enable sample_weight balancing for imbalanced classes')
    parser.add_argument('--early_stopping_rounds',         type=int,                          help='e.g. 150 (stop if no improvement for N rounds)')
    parser.add_argument('--n_iter',                        type=int,                          help='e.g. 200 (BayesSearchCV iterations)')
    parser.add_argument('--cv',                            type=int,                          help='e.g. 5 (TimeSeriesSplit folds), use 2 for quick debug')
    parser.add_argument('--random_state',                  type=int,                          help='e.g. 42 (random seed for reproducibility)')
    parser.add_argument('--scoring',                       type=str, choices=['accuracy', 'neg_log_loss'], help='CV scoring metric')
    parser.add_argument('--exclude_cols',                  nargs='*',                                     help='feature columns to exclude from training')
    return parser.parse_args()

def build_payload(args: argparse.Namespace) -> dict:
    payload = {
        "dataset_name": args.dataset_name,
        "objective":    {"balanced": args.balanced},
        "model":        {"params": {}},
        "optimizer":    {"params": {}},
    }

    if args.test_set_size is not None:
        payload["objective"]["test_set_size"] = args.test_set_size
    if args.eval_set_size is not None:
        payload["objective"]["eval_set_size"] = args.eval_set_size
    if args.calibration_set_size is not None:
        payload["objective"]["calibration_set_size"] = args.calibration_set_size
    if args.early_stopping_rounds is not None:
        payload["model"]["params"]["early_stopping_rounds"] = args.early_stopping_rounds
    if args.random_state is not None:
        payload["model"]["params"]["random_state"] = args.random_state
        payload["optimizer"]["params"]["random_state"] = args.random_state
    if args.n_iter is not None:
        payload["optimizer"]["params"]["n_iter"] = args.n_iter
    if args.cv is not None:
        payload["optimizer"]["params"]["cv"] = args.cv
    if args.scoring is not None:
        payload["optimizer"]["params"]["scoring"] = args.scoring
    if args.exclude_cols is not None:
        payload["objective"]["exclude_cols"] = args.exclude_cols

    return payload

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

    try:
        WinballTrainer(build_payload(args)).train()
    finally:
        get_postgresql_manager().cleanup()

if __name__ == "__main__":
    main()
