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
from core.types.enums import SiteName, ModelFamily


@TaskRegistry.poll('build.fotmob.prediction')
class BuildMatchPrediction(PollTask):
    MAX_CLUD_LEAGUES = 300

    def __init__(self, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__()
        self.match_dao = MatchDao()
        self.fixture_dao = ActiveFixtureDao()
        self.training_record_dao = TrainingRecordDao()
        self.predict_service = get_predict_service()
        self.league_service = get_league_service()

        self.retry_interval = timedelta(minutes=5)
        self.rebuild_strategy = (
            TimelineStrategy(min_interval=timedelta(minutes=15))
            .add_segment(start_offset=timedelta(hours=-48), end_offset=timedelta(hours=-6),  interval=timedelta(hours=2))
            .add_segment(start_offset=timedelta(hours=-6),  end_offset=timedelta(hours=-2),  interval=timedelta(hours=1))
            .add_segment(start_offset=timedelta(hours=-2),  end_offset=timedelta(hours=0),   interval=timedelta(minutes=15))
        )

    def get_pending_predict_items(self) -> List[Any]:
        club_record    = self.training_record_dao.get_recommended(ModelFamily.WINBALL_CLUB)
        national_record = self.training_record_dao.get_recommended(ModelFamily.WINBALL_NATIONAL)

        if not club_record and not national_record:
            self.logger.warning("No default model available, skipping prediction")
            return []

        min_kickoff_time = datetime.now(timezone.utc)
        max_kickoff_time = min_kickoff_time + ModelService.PREDICTION_LOOKAHEAD

        site_leagues = self.league_service.get_site_leagues(SiteName.FOTMOB.value)
        club_league_ids    = [league.league_id for league in site_leagues if league.ref_league_id <= self.MAX_CLUD_LEAGUES]
        national_league_ids = [league.league_id for league in site_leagues if league.ref_league_id > self.MAX_CLUD_LEAGUES]

        items = []
        for record, league_ids in zip((club_record, national_record), (club_league_ids, national_league_ids)):
            if record is None:
                continue

            if not league_ids:
                continue

            self.predict_service.load_predictor(record.model_family, record.model_version, record)
            pending = self.match_dao.get_pending_predict_items(
                record.model_version, league_ids, min_kickoff_time, max_kickoff_time
            )
            items += [(item, record) for item in pending]
        return items

    def execute(self, *args, **kwargs) -> None:
        self.idle_sleep()
        while not self.should_stop():
            try:
                items = self.get_pending_predict_items()
                if not items:
                    continue

                for (match_code, kickoff_time), record in items:
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
                            "match_code":    match_code,
                            "model_version": result['model_version'],
                            "home_prob":     probabilities.get('2', 0.0),
                            "draw_prob":     probabilities.get('1', 0.0),
                            "away_prob":     probabilities.get('0', 0.0),
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
            finally:
                self.idle_sleep()
