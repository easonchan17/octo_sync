from typing import Optional, Dict, Any
from core.registry import Registry
from core.scheduler.tasks.analysis.training.winball.winball_trainer import WinballTrainer
from core.scheduler.tasks.base_task import BaseTask, Pipeline
from core.store.postgres.postgresql_manager import PostgreSQLManager
from core.store.postgres.models import Site, TrainingRecord
from core.scheduler.tasks.analysis.inference.base_predictor import BasePredictor
from core.scheduler.tasks.analysis.inference.winball.winball_predictor import WinballPredictor
from core.scheduler.tasks.analysis.analyzers.match_stats_aggregator import MatchStatsAggregator

@Registry.factory('winball.fbref.samples')
def create_winball_fbref_samples_task(
    site: Site,
    db: PostgreSQLManager,
    payload: Optional[Dict[str, Any]]
) -> BaseTask:
    return Pipeline(
        MatchStatsAggregator(site, payload)
    )

@Registry.factory('winball.training')
def create_winball_training_task(
    site: Site,
    db: PostgreSQLManager,
    payload: Optional[Dict[str, Any]]
) -> BaseTask:
    db.create_tables(
        [TrainingRecord]
    )
    return Pipeline(
        WinballTrainer(site, payload)
    )

@Registry.factory('winball.inference')
def create_winball_inference_instance(
    site: Site,
    db: PostgreSQLManager,
    payload: Optional[Dict[str, Any]]
) -> BasePredictor:
    return WinballPredictor()
