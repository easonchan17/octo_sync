from typing import Dict, Any, Optional
from core.tasks.poll_task import PollTask
from datetime import datetime, timedelta, timezone
from core.scheduler.task_registry import TaskRegistry
from core.store.postgres.daos.fotmob.form_cache_dao import FormCacheDao
from core.services.ml.inference.predict_service import get_predict_service


@TaskRegistry.poll('build.fotmob.form_cache')
class BuildFormCache(PollTask):
    POLL_IDLE_SECONDS = 300
    DEBOUNCE_WINDOW = timedelta(minutes=10)
    LOOKBACK_WINDOW = timedelta(days=365)

    def __init__(self, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__()
        self.form_cache_dao  = FormCacheDao()
        self.predict_service = get_predict_service()

    def execute(self, *args, **kwargs) -> None:
        last_check_time, last_signal_time = datetime.now(timezone.utc), datetime.min.replace(tzinfo=timezone.utc)

        while not self.should_stop():
            try:
                current_time = datetime.now(timezone.utc)
                min_kickoff_time = current_time - self.LOOKBACK_WINDOW

                updated_count = self.form_cache_dao.count_updated_since(last_check_time, min_kickoff_time)
                last_check_time = current_time

                if updated_count > 0:
                    last_signal_time = last_check_time
                    self.logger.info(f"Detected {updated_count} fixture updates, debounce reset")
                    continue

                if last_signal_time is not None and last_check_time - last_signal_time >= self.DEBOUNCE_WINDOW:
                    match_count = self.predict_service.build_form_cache(min_kickoff_time)
                    self.form_cache_dao.add_build_log(min_kickoff_time, match_count)
                    last_signal_time = None
                    self.logger.info(f"FormCache built: match_count={match_count}, checkpoint={min_kickoff_time}")
            except Exception as e:
                self.logger.error(f"BuildFormCache error: {e}", exc_info=True)
            finally:
                self.idle_sleep()
