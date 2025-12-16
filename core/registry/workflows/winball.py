from typing import Optional, Dict, Any
from core.registry.registry import Registry
from core.scheduler.tasks.analysis.training.winball.winball_trainer import WinballTrainer
from core.scheduler.tasks.base_task import BaseTask, Pipeline
from core.store.postgres.postgresql_manager import PostgreSQLManager
from core.store.postgres.models import Site, TrainingRecord
from core.scheduler.tasks.analysis.inference.base_predictor import BasePredictor
from core.scheduler.tasks.analysis.inference.winball.winball_predictor import WinballPredictor
from core.scheduler.tasks.analysis.analyzers.match_stats_aggregator import MatchStatsAggregator

@Registry.register('analysis.winball.match_stats')
def create_analysis_fbref_match_stats_task(
    site: Site,
    db: PostgreSQLManager,
    payload: Optional[Dict[str, Any]]
) -> BaseTask:
    return Pipeline(
        MatchStatsAggregator(site, payload)
    )


@Registry.register('training.winball')
def create_training_winball_task(
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


@Registry.register('inference.winball')
def create_inference_winball_instance(
    site: Site,
    db: PostgreSQLManager,
    payload: Optional[Dict[str, Any]]
) -> BasePredictor:
    return WinballPredictor()
