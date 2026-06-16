import sys
import signal
import argparse
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

if Path('.').resolve() != Path(__file__).resolve().parents[1]:
    sys.exit(f"Must be run from project root: {Path(__file__).resolve().parents[1]}")

from core.config.config_manager import get_config_manager
from core.logger.logger_manager import get_logger_manager
from core.store.postgres.postgresql_manager import get_postgresql_manager
from core.store.postgres.daos.common import TrainingRecordDao
from core.services.ml.models.xgboost_classifier import XGBoostClassifier
from core.services.ml.training.train_config import WinballClubTrainConfig, WinballNationalTrainConfig
from core.services.ml.training.train_tracker import TrainTracker
from core.types.enums import ModelFamily
from core.utils.pandas_utils import load_dataframe

logger = get_logger_manager().get_logger(__name__)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Re-evaluate a saved winball model')
    parser.add_argument('--config',        '-c', type=str, default='configs/config.yml')
    parser.add_argument('--model_version', '-v', type=str, required=True)
    parser.add_argument('--model_family',        type=str, default=ModelFamily.WINBALL_CLUB, choices=[f.value for f in ModelFamily])
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

    try:
        record = TrainingRecordDao().get_by_version(args.model_version)

        config_map = {
            ModelFamily.WINBALL_CLUB:     WinballClubTrainConfig,
            ModelFamily.WINBALL_NATIONAL: WinballNationalTrainConfig,
        }
        config_cls = config_map[ModelFamily(args.model_family)]
        config = config_cls({
            'dataset_name': record.dataset_name,
            'objective':    {'balanced': record.training_params.get('balanced', False)},
        })

        df = load_dataframe(config.dataset_dir / record.dataset_name)
        TrainTracker.validate_dataset(df)

        y = df[config.target_col].copy()
        X = df[record.feature_names]

        test_set_size = record.training_params['test_set_size']
        test_split  = int(len(X) * (1 - test_set_size))
        calib_split = int(len(X) * (1 - test_set_size - config.calibration_set_size))

        X_test  = X.iloc[test_split:].copy()
        y_test  = y.iloc[test_split:].copy()
        X_calib = X.iloc[calib_split:test_split].copy()
        y_calib = y.iloc[calib_split:test_split].copy()
        market_probs_test  = df.iloc[test_split:][TrainTracker.MARKET_BASELINE_COLS].values
        market_probs_calib = df.iloc[calib_split:test_split][TrainTracker.MARKET_BASELINE_COLS].values
        market_vig_test    = df.iloc[test_split:][[TrainTracker.MARKET_VIG_COL]].values.flatten()

        model_path = Path(record.model_path)
        if not model_path.is_absolute():
            model_path = Path.cwd() / model_path
        eval_set_size = record.training_params.get('eval_set_size', 0.1)
        model_params  = record.training_params.get('model_params', {})
        estimator = XGBoostClassifier.load_from_file(str(model_path), eval_set_size=eval_set_size, **model_params)

        tracker = TrainTracker(config)
        tracker.optimizer = SimpleNamespace(
            best_estimator_=estimator,
            best_score_=-record.train_score,
            best_params_=record.best_params,
        )
        tracker.analysis(
            X_test, y_test, market_probs_test, market_vig_test, market_probs_calib, X_calib, y_calib
        )
        tracker.report(record.model_version)
    finally:
        get_postgresql_manager().cleanup()


if __name__ == "__main__":
    main()
