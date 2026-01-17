from sqlalchemy import or_
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models import MatchResult, Site, MatchStatsSyncFlag
from core.store.postgres.models.fbref.match_fixture import MatchFixture
from .team_level_synchronizer import TeamLevelSynchronizer
from ..common import SysValSynchronizer

class ScoresAndFixturesSynchronizer(TeamLevelSynchronizer):
    ELO_IMPACT_FIELDS = [
        MatchResult.kickoff_time.key,
        MatchResult.home_gf.key,
        MatchResult.away_gf.key,
        MatchResult.comp_code.key,
        MatchResult.home_code.key,
        MatchResult.away_code.key
    ]

    def __init__(self) -> None:
        super().__init__()
        self.sys_val_synchronizer = SysValSynchronizer()

    def sync(
        self,
        site: Site,
        team_name: str,
        team_code: str,
        season: int,
        match_results: List[Dict[str, Any]],
        match_fixtures: List[Dict[str, Any]]
    ) -> None:
        with self.db.get_session(site.get_namespace()) as session:
            self._sync_match_results(session, site, team_name, team_code, season, match_results)
            self._sync_match_fixtures(session, site, team_name, team_code, season, match_fixtures)

    def _sync_match_results(
        self,
        session: Session,
        site: Site,
        team_name: str,
        team_code: str,
        season: int,
        match_results: List[Dict[str, Any]]
    ) -> None:
        if not match_results:
            self.logger.warning(f"No {team_name} {season}-{season+1} match results to sync from {site.name}")
            return

        kickoff_time_key = MatchResult.kickoff_time.key
        match_results.sort(key=lambda x: x.get(kickoff_time_key))
        last_synced_time = match_results[-1].get(kickoff_time_key)

        impact_time = self._find_min_impact_time(session, match_results)
        if impact_time:
            self.sys_val_synchronizer.set_val('elo_impact_time', impact_time)

        insert_stmt = insert(MatchResult).values(match_results)
        assignment, where_clause = self.build_upsert_clauses(
            MatchResult,
            insert_stmt,
            {
                MatchResult.id.key,
                MatchResult.created_at.key,
                MatchResult.match_code.key,
                MatchResult.updated_at.key
            }
        )
        insert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=[MatchResult.match_code.key],
            set_=assignment,
            where=where_clause
        )
        result = session.execute(insert_stmt)
        upserted_count = result.rowcount
        self.logger.info(f"Sync {team_name} {season}-{season+1} match results from {site.name} completed. upserted: {upserted_count}")

        self.update_sync_state(
            session,
            team_code,
            season,
            MatchStatsSyncFlag.MATCH_RESULT,
            last_synced_time
        )
        self.logger.info(f"Mark {site.name} {team_name} {season}-{season+1} match results as synced")

    def _sync_match_fixtures(
        self,
        session: Session,
        site: Site,
        team_name: str,
        team_code: str,
        season: int,
        match_fixtures: List[Dict[str, Any]]
    ) -> None:
        deleted_count = session.query(MatchFixture).filter(
            or_(
                MatchFixture.home_code == team_code,
                MatchFixture.away_code == team_code
            ),
            MatchFixture.season == season
        ).delete(synchronize_session=False)
        self.logger.info(f"Delete {team_name} {season}-{season+1} existing match fixtures from {site.name} completed. deleted: {deleted_count}")

        if not match_fixtures:
            self.logger.warning(f"No {team_name} {season}-{season+1} match fixtures to sync from {site.name}")
            return

        insert_stmt = insert(MatchFixture).values(match_fixtures)
        result = session.execute(insert_stmt)
        inserted_count = result.rowcount
        self.logger.info(f"Sync {team_name} {season}-{season+1} match fixtures from {site.name} completed. inserted: {inserted_count}")

    def _find_min_impact_time(
        self,
        session: Session,
        match_results: List[Dict[str, Any]]
    ) -> Optional[datetime]:

        match_code_key = MatchResult.match_code.key
        kickoff_time_key = MatchResult.kickoff_time.key

        match_codes = [item[match_code_key] for item in match_results]
        existing_records = session.query(MatchResult).filter(
            MatchResult.match_code.in_(match_codes)
        ).all()
        existing_map = {record.match_code: record for record in existing_records}

        min_impact_time: Optional[datetime] = None

        for new_item in match_results:
            match_code = new_item[match_code_key]
            old_item = existing_map.get(match_code) # MatchResult Object or None

            impact_time: Optional[datetime] = None

            if not old_item:
                impact_time = new_item.get(kickoff_time_key)
            elif not old_item.is_same(new_item, self.ELO_IMPACT_FIELDS):
                impact_time = min(getattr(old_item, kickoff_time_key), new_item.get(kickoff_time_key))

            if impact_time:
                if min_impact_time is None or impact_time < min_impact_time:
                    min_impact_time = impact_time

        return min_impact_time