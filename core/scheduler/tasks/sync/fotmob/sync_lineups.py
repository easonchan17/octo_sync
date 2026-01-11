from typing import Any, Dict, Optional
from core.store.postgres.models import Site
from datetime import datetime, timedelta, timezone
from core.browser.interceptor import TaskType
from core.scheduler.tasks.base_task import BaseTask
from core.browser.intercept_policy import InterceptPolicy
from core.browser.components.receivers.fotmob.lineup_receiver import LineupReceiver
from core.scheduler.synchronizers.fotmob.lineup_synchronizer import LineupSynchronizer
from core.browser.components.senders.fotmob.search_lineup_sender import SearchLineupSender

class SyncLineups(BaseTask):
    DEFAULT_LOOKAHEAD_HOURS = 48

    # Time window thresholds in seconds
    CUTOFF_BUFFER_SECONDS = 15 * 60      # Post-match cutoff buffer (15 minutes)
    SPRINT_WINDOW_SECONDS = 60 * 60      # Sprint window (1 hour before kickoff)
    AMBUSH_WINDOW_SECONDS = 2 * 60 * 60  # Ambush window (2 hours before kickoff)

    # Fetch intervals in seconds
    INTERVAL_SPRINT = 2 * 60             # High frequency: 2 minutes
    INTERVAL_AMBUSH = 15 * 60            # Medium frequency: 15 minutes
    INTERVAL_HOARD  = 12 * 60 * 60       # Low frequency: 12 hours

    POLICY_CONFIG = {
        "url_template": "https://www.fotmob.com{page_url}",
        "debug": False,
        "rules": [
            {
                "type": "http",
                "pattern": "https://www.fotmob.com/api/data/matchDetails",
                "sender": SearchLineupSender,
                "receiver": LineupReceiver
            }
        ]
    }

    def __init__(self, site: Site, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__()
        self.site = site
        self.payload = payload or {}
        self.synchronizer = LineupSynchronizer()

    def _should_fetch(self, kickoff_time: datetime, last_synced_at: Optional[datetime]) -> bool:
        if last_synced_at is None:
            return True

        now = datetime.now(timezone.utc)
        seconds_to_kickoff = (kickoff_time - now).total_seconds()
        seconds_since_sync = (now - last_synced_at).total_seconds()

        # 1. Cutoff check: skip if match ended more than buffer period ago
        if seconds_to_kickoff < -self.CUTOFF_BUFFER_SECONDS:
            return False

        # 2. Sprint window: within 1 hour before kickoff
        if seconds_to_kickoff <= self.SPRINT_WINDOW_SECONDS:
            return seconds_since_sync >= self.INTERVAL_SPRINT

        # 3. Ambush window: 1-2 hours before kickoff
        if seconds_to_kickoff <= self.AMBUSH_WINDOW_SECONDS:
            return seconds_since_sync >= self.INTERVAL_AMBUSH

        # 4. Hoard window: more than 2 hours before kickoff
        return seconds_since_sync >= self.INTERVAL_HOARD

    def execute(self, *args, **kwargs) -> None:
        start_time = datetime.now(timezone.utc)
        lookahead_hours = self.payload.get("lookahead_hours", self.DEFAULT_LOOKAHEAD_HOURS)
        end_time = start_time + timedelta(hours=lookahead_hours)

        tasks = self.synchronizer.get_pending_tasks(self.site, start_time, end_time)
        if not tasks:
            self.logger.warning(f"No pending tasks found for upcoming fixtures within {lookahead_hours} hours")
            return

        intercept_policy = InterceptPolicy.from_rules(self.POLICY_CONFIG)
        for kickoff_time, home_team, away_team, page_url, last_synced_at in tasks:
            if self.should_stop():
                return

            if not self._should_fetch(kickoff_time, last_synced_at):
                continue

            try:
                match_detail_url = intercept_policy.url.format(page_url=page_url)
                future = self.interceptor.submit_task(
                    TaskType.OPEN_PAGE,
                    url=match_detail_url,
                    intercept_policy=intercept_policy
                )

                responses, _ = future.result()
                if not responses:
                    self.logger.error(f"No response for {match_detail_url}")
                    continue

                lineup = responses[0]
                if not lineup:
                    self.logger.warning(f"No lineup data for {match_detail_url}")
                    continue

                self.synchronizer.sync(self.site, home_team, away_team, lineup)
            except Exception as e:
                self.logger.error(f"Failed to sync lineups for match {home_team} vs {away_team} from {self.site.name}: {e}")
