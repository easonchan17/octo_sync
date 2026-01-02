from sqlalchemy import func
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.dialects.postgresql import insert
from core.utils.singleton import Singleton
from core.store.postgres.models import MatchCursor, MatchStatus
from core.store.postgres.models.fotmob.fixture import Fixture
from core.config.league_config import get_league_metadata
from ..base_synchronizer import BaseSynchronizer

class MatchCursorSynchronizer(BaseSynchronizer, Singleton):
    def sync(self, site_name: str, league_id: int, fixtures: List[Dict[str, Any]]) -> None:
        if not fixtures:
            self.logger.warning(f"No fixtures to sync from {site_name}")
            return

        metadata = get_league_metadata(league_id, site_name)

        comp_code = metadata["id"]
        comp_name = metadata["name"]

        cursors = self.extract_cursors(comp_code, fixtures)
        self.persist_cursors(comp_code, comp_name, cursors)

    def extract_cursors(self, comp_code: str, fixtures: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        kickoff_time_key = Fixture.kickoff_time.key
        match_status_key = Fixture.match_status.key
        home_id_key = Fixture.home_id.key
        away_id_key = Fixture.away_id.key

        cursors: Dict[str, datetime] = {}

        for fixture in fixtures:
            if not MatchStatus(fixture[match_status_key]).is_finished:
                continue

            kickoff_time = fixture[kickoff_time_key]

            home_code = fixture[home_id_key]
            home_name = fixture[home_team_key]
            home_cursor = cursors.get(home_code)
            if home_cursor is None or kickoff_time > home_cursor:
                cursors[home_code] = {
                    kickoff_time
                }

            away_code = fixture[away_id_key]
            away_name = fixture[away_team_key]
            away_cursor = cursors.get(away_code)
            if away_cursor is None or kickoff_time > away_cursor:
                cursors[away_code] = {
                    kickoff_time
                }

        return [
            {
                MatchCursor.comp_code.key: comp_code,
                MatchCursor.team_code.key: team_code,
                MatchCursor.team_name.key: team_name,
                MatchCursor.last_kickoff_time.key: kickoff_time
            }
            for team_code, kickoff_time in cursors.items()
        ]

    def persist_cursors(self, comp_code: str, comp_name: str, cursors: List[Dict[str, Any]]) -> None:
        with self.db.get_session() as session:
            insert_stmt = insert(MatchCursor).values(cursors)
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[MatchCursor.comp_code.key, MatchCursor.team_code.key],
                set_={
                    MatchCursor.last_kickoff_time.key: insert_stmt.excluded.last_kickoff_time,
                    MatchCursor.updated_at.key: func.now()
                },
                where=insert_stmt.excluded.last_kickoff_time > MatchCursor.last_kickoff_time
            )
            result = session.execute(insert_stmt)
            upserted_count = result.rowcount
            self.logger.info(f"Sync {comp_name}({comp_code}) match cursors completed. upserted: {upserted_count}")