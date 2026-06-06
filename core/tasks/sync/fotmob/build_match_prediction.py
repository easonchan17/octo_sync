from typing import Any, Dict, List, Optional
from core.tasks.poll_task import PollTask
from datetime import datetime, timedelta, timezone
from core.scheduler.task_registry import TaskRegistry
from core.tasks.refetch_strategy import TimelineStrategy
from core.store.postgres.daos.fotmob import MatchDao, ActiveFixtureDao
from core.store.postgres.daos.common import TrainingRecordDao
from core.services.ml.inference.predict_service import get_predict_service
from core.services.model_service import ModelService
from core.services.league import get_league_service
from core.types.enums import SiteName


@TaskRegistry.poll('build.fotmob.prediction')
class BuildMatchPrediction(PollTask):
    def __init__(self, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__()
        self.match_dao = MatchDao()
        self.fixture_dao = ActiveFixtureDao()
        self.training_record_dao = TrainingRecordDao()
        self.predict_service = get_predict_service()
        self.league_service = get_league_service()

        self.retry_interval = timedelta(minutes=5)
        self.rebuild_strategy = (
            TimelineStrategy(min_interval=timedelta(minutes=30))
            .add_segment(start_offset=timedelta(hours=-48), end_offset=timedelta(hours=-6),  interval=timedelta(hours=4))
            .add_segment(start_offset=timedelta(hours=-6),  end_offset=timedelta(hours=-2),  interval=timedelta(hours=1))
            .add_segment(start_offset=timedelta(hours=-2),  end_offset=timedelta(hours=0),   interval=timedelta(minutes=30))
        )

    def get_pending_predict_items(self, model_version: str) -> List[Any]:
        min_kickoff_time = datetime.now(timezone.utc)
        site_leagues = self.league_service.get_site_leagues(SiteName.FOTMOB.value)
        league_ids = [league.league_id for league in site_leagues]

        return self.match_dao.get_pending_predict_items(
            model_version,
            league_ids,
            min_kickoff_time,
            min_kickoff_time + ModelService.PREDICTION_LOOKAHEAD
        )

    def execute(self, *args, **kwargs) -> None:
        while not self.should_stop():
            try:
                record = self.training_record_dao.get_default()
                if record is None:
                    self.logger.warning("No default model available, skipping prediction")
                    self.idle_sleep()
                    continue

                items = self.get_pending_predict_items(record.model_version)
                if not items:
                    self.idle_sleep()
                    continue

                for match_id, match_code, kickoff_time in items:
                    if self.should_stop():
                        return

                    try:
                        fixture = self.fixture_dao.get_by_match_code(match_code)
                        if fixture is None:
                            continue

                        result = self.predict_service.predict(fixture, record.model_version)
                        probabilities = result['probabilities']

                        current_time = datetime.now(timezone.utc)
                        self.match_dao.sync_predict_data({
                            "match_id":      match_id,
                            "match_code":    match_code,
                            "model_version": result['model_version'],
                            "home_prob":     probabilities.get('0', 0.0),
                            "draw_prob":     probabilities.get('1', 0.0),
                            "away_prob":     probabilities.get('2', 0.0),
                            "prediction":    result['prediction'],
                            "predicted_at":  current_time,
                        })
                        self.match_dao.reschedule_prediction(
                            match_code,
                            result['model_version'],
                            self.rebuild_strategy.suggest_interval(kickoff_time, current_time)
                        )
                        self.logger.info(f"Predicted match: match_code={match_code}")
                    except Exception as e:
                        self.logger.error(f"Failed to predict match {match_code}: {e}")
                        retry_interval = None if datetime.now(timezone.utc) >= kickoff_time + self.retry_interval else self.retry_interval
                        self.match_dao.reschedule_prediction(match_code, record.model_version, retry_interval)

            except Exception as e:
                self.logger.error(f"PredictMatch error: {e}", exc_info=True)
                self.idle_sleep()
