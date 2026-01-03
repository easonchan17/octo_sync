from typing import List, Any, Optional, Dict
from sqlalchemy import func, or_
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models import (
    PlayerMatchStats, Site, PlayerStatsSyncState,
    PlayerStatsSyncFlag, MatchResult, Status
)
from ..base_synchronizer import BaseSynchronizer

class PlayerMatchStatsSynchronizer(BaseSynchronizer):
    def get_pending_tasks(
        self,
        site: Site,
        min_season: int,
        max_season: int,
        sync_flag: int,
        comp_code: Optional[str] = None,
        team_code: Optional[str] = None
    ) -> List[Any]:
        if not comp_code and not team_code:
            raise ValueError("Either comp_code or team_code must be provided")

        with self.db.get_session(site.get_namespace()) as session:
            query = session.query(
                MatchResult.match_code,
                MatchResult.home_team,
                MatchResult.away_team,
                MatchResult.season,
                MatchResult.match_report
            ).outerjoin(
                PlayerStatsSyncState,
                PlayerStatsSyncState.match_code == MatchResult.match_code
            ).filter(
                MatchResult.status.op('&')(Status.ACTIVE.value) == Status.ACTIVE.value,
                MatchResult.season.between(min_season, max_season),
                or_(
                    PlayerStatsSyncState.match_code.is_(None),
                    (PlayerStatsSyncState.sync_flags.op('&')(sync_flag)) != sync_flag
                )
            )

            if comp_code:
                query = query.filter(MatchResult.comp_code == comp_code)
            if team_code:
                query = query.filter(
                    or_(
                        MatchResult.home_code == team_code,
                        MatchResult.away_code == team_code
                    )
                )

            return query.order_by(MatchResult.season, MatchResult.kickoff_time).all()

    def sync(self, site: Site, match_code: str, home_team: str, away_team: str, season: int, player_stats: List[Dict[str, Any]]) -> None:
        match_tag = f"{season} {home_team} vs {away_team}"

        if not player_stats:
            self.logger.warning(f"No player match stats to sync for match {match_tag} from {site.name}")
            return

        with self.db.get_session(site.get_namespace()) as session:
            insert_stmt = insert(PlayerMatchStats).values(player_stats)
            assignment, where_clause = self.build_upsert_clauses(
                PlayerMatchStats,
                insert_stmt,
                {
                    PlayerMatchStats.id.key,
                    PlayerMatchStats.created_at.key,
                    PlayerMatchStats.match_code.key,
                    PlayerMatchStats.player_code.key,
                    PlayerMatchStats.updated_at.key
                }
            )
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[PlayerMatchStats.match_code.key, PlayerMatchStats.player_code.key],
                set_=assignment,
                where=where_clause
            )
            result = session.execute(insert_stmt)
            upserted_count = result.rowcount
            self.logger.info(f"Sync player match stats for match {match_tag} from {site.name} completed. upserted: {upserted_count}")

            insert_flag_stmt = insert(PlayerStatsSyncState).values(
                match_code=match_code,
                sync_flags=PlayerStatsSyncFlag.PLAYER_STATS.value
            )
            insert_flag_stmt = insert_flag_stmt.on_conflict_do_update(
                index_elements=[PlayerStatsSyncState.match_code.key],
                set_={
                    PlayerStatsSyncState.sync_flags.key: PlayerStatsSyncState.sync_flags.op('|')(PlayerStatsSyncFlag.PLAYER_STATS.value),
                    PlayerStatsSyncState.updated_at.key: func.now()
                }
            )
            session.execute(insert_flag_stmt)
            self.logger.info(f"Mark match {match_tag} players stats as synced")
