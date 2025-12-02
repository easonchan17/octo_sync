from typing import List, Any, Tuple
from sqlalchemy import func, or_, and_
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models import (
    PlayerMatchStats, Site, MatchStatus, MatchSyncFlag, Fixture
)
from ..base_synchronizer import BaseSynchronizer

class PlayerMatchStatsSynchronizer(BaseSynchronizer):
    def get_unsynced_fixtures(
        self,
        site: Site,
        clubs: List[Tuple[str, str]],
        min_season: int,
        max_season: int,
        sync_flag: int
    ) -> List[Tuple[str, str]]:
        club_codes = [club_code for _, club_code in clubs]

        with self.postgresql_manager.get_session(site.get_namespace()) as session:
            query = session.query(
                Fixture.code,
                Fixture.home_team,
                Fixture.away_team,
                Fixture.season,
                Fixture.match_report
            ).outerjoin(
                MatchStatus,
                MatchStatus.code == Fixture.code
            ).filter(
                Fixture.status == 1,
                or_(
                    Fixture.home_code.in_(club_codes),
                    Fixture.away_code.in_(club_codes)
                ),
                Fixture.season.between(min_season, max_season),
                or_(
                    MatchStatus.code.is_(None),
                    (MatchStatus.sync_flags.op('&')(sync_flag)) != sync_flag
                )
            )
            return query.all()

    def sync(self, site: Site, fixture: Fixture, player_stats: List[PlayerMatchStats]) -> None:
        match_tag = f"{fixture.season} {fixture.home_team} vs {fixture.away_team}"

        if not player_stats:
            self.logger.warning(f"No player match stats to sync for match {match_tag} from {site.name}")
            return

        player_stats_dict = self.to_dict(
            player_stats,
            ['match_code', 'player_code', 'team_code', 'player_name', 'position', 'minutes', 'is_starter', 'goals', 'shots', 'shots_on_target', 'npxg',
             'xg_assist', 'shot_creating_actions', 'progressive_passes', 'key_passes',
             'progressive_carries', 'take_ons_won', 'fouls_drawn', 'dispossessed', 'miscontrols',
             'tackles', 'tackles_won', 'blocks', 'interceptions', 'ball_recoveries', 'challenges_lost',
             'aerials_won', 'aerials_lost',
             'gk_goals_against', 'gk_psxg', 'gk_crosses', 'gk_crosses_stopped', 'gk_def_actions_outside_pen_area'],
            ['match_code', 'player_code']
        )

        with self.postgresql_manager.get_session(site.get_namespace()) as session:
            insert_stmt = insert(PlayerMatchStats).values(list(player_stats_dict.values()))
            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=['match_code', 'player_code'],
                set_={
                    'team_code': insert_stmt.excluded.team_code,
                    'player_name': insert_stmt.excluded.player_name,
                    'position': insert_stmt.excluded.position,
                    'minutes': insert_stmt.excluded.minutes,
                    'is_starter': insert_stmt.excluded.is_starter,
                    'goals': insert_stmt.excluded.goals,
                    'shots': insert_stmt.excluded.shots,
                    'shots_on_target': insert_stmt.excluded.shots_on_target,
                    'npxg': insert_stmt.excluded.npxg,
                    'xg_assist': insert_stmt.excluded.xg_assist,
                    'shot_creating_actions': insert_stmt.excluded.shot_creating_actions,
                    'progressive_passes': insert_stmt.excluded.progressive_passes,
                    'key_passes': insert_stmt.excluded.key_passes,
                    'progressive_carries': insert_stmt.excluded.progressive_carries,
                    'take_ons_won': insert_stmt.excluded.take_ons_won,
                    'fouls_drawn': insert_stmt.excluded.fouls_drawn,
                    'dispossessed': insert_stmt.excluded.dispossessed,
                    'miscontrols': insert_stmt.excluded.miscontrols,
                    'tackles': insert_stmt.excluded.tackles,
                    'tackles_won': insert_stmt.excluded.tackles_won,
                    'blocks': insert_stmt.excluded.blocks,
                    'interceptions': insert_stmt.excluded.interceptions,
                    'ball_recoveries': insert_stmt.excluded.ball_recoveries,
                    'challenges_lost': insert_stmt.excluded.challenges_lost,
                    'aerials_won': insert_stmt.excluded.aerials_won,
                    'aerials_lost': insert_stmt.excluded.aerials_lost,
                    'gk_goals_against': insert_stmt.excluded.gk_goals_against,
                    'gk_psxg': insert_stmt.excluded.gk_psxg,
                    'gk_crosses': insert_stmt.excluded.gk_crosses,
                    'gk_crosses_stopped': insert_stmt.excluded.gk_crosses_stopped,
                    'gk_def_actions_outside_pen_area': insert_stmt.excluded.gk_def_actions_outside_pen_area,
                    'update_at': func.now()
                },
                where=(
                    or_(
                        PlayerMatchStats.team_code != insert_stmt.excluded.team_code,
                        PlayerMatchStats.player_name != insert_stmt.excluded.player_name,
                        PlayerMatchStats.position != insert_stmt.excluded.position,
                        PlayerMatchStats.minutes != insert_stmt.excluded.minutes,
                        PlayerMatchStats.is_starter != insert_stmt.excluded.is_starter,
                        PlayerMatchStats.goals != insert_stmt.excluded.goals,
                        PlayerMatchStats.shots != insert_stmt.excluded.shots,
                        PlayerMatchStats.shots_on_target != insert_stmt.excluded.shots_on_target,
                        PlayerMatchStats.npxg != insert_stmt.excluded.npxg,
                        PlayerMatchStats.xg_assist != insert_stmt.excluded.xg_assist,
                        PlayerMatchStats.shot_creating_actions != insert_stmt.excluded.shot_creating_actions,
                        PlayerMatchStats.progressive_passes != insert_stmt.excluded.progressive_passes,
                        PlayerMatchStats.key_passes != insert_stmt.excluded.key_passes,
                        PlayerMatchStats.progressive_carries != insert_stmt.excluded.progressive_carries,
                        PlayerMatchStats.take_ons_won != insert_stmt.excluded.take_ons_won,
                        PlayerMatchStats.fouls_drawn != insert_stmt.excluded.fouls_drawn,
                        PlayerMatchStats.dispossessed != insert_stmt.excluded.dispossessed,
                        PlayerMatchStats.miscontrols != insert_stmt.excluded.miscontrols,
                        PlayerMatchStats.tackles != insert_stmt.excluded.tackles,
                        or_(
                            PlayerMatchStats.tackles_won != insert_stmt.excluded.tackles_won,
                            and_(
                                PlayerMatchStats.tackles_won.is_(None),
                                insert_stmt.excluded.tackles_won.isnot(None)
                            ),
                            and_(
                                PlayerMatchStats.tackles_won.isnot(None),
                                insert_stmt.excluded.tackles_won.is_(None)
                            )
                        ),
                        PlayerMatchStats.blocks != insert_stmt.excluded.blocks,
                        PlayerMatchStats.interceptions != insert_stmt.excluded.interceptions,
                        PlayerMatchStats.ball_recoveries != insert_stmt.excluded.ball_recoveries,
                        PlayerMatchStats.challenges_lost != insert_stmt.excluded.challenges_lost,
                        PlayerMatchStats.aerials_won != insert_stmt.excluded.aerials_won,
                        PlayerMatchStats.aerials_lost != insert_stmt.excluded.aerials_lost,
                        PlayerMatchStats.gk_goals_against != insert_stmt.excluded.gk_goals_against,
                        PlayerMatchStats.gk_psxg != insert_stmt.excluded.gk_psxg,
                        PlayerMatchStats.gk_crosses != insert_stmt.excluded.gk_crosses,
                        PlayerMatchStats.gk_crosses_stopped != insert_stmt.excluded.gk_crosses_stopped,
                        PlayerMatchStats.gk_def_actions_outside_pen_area != insert_stmt.excluded.gk_def_actions_outside_pen_area
                    )
                )
            )
            result = session.execute(insert_stmt)
            upserted_count = result.rowcount
            self.logger.info(f"Sync player match stats for match {match_tag} from {site.name} completed. upserted: {upserted_count}")

            insert_flag_stmt = insert(MatchStatus).values(
                code=fixture.code,
                sync_flags=MatchSyncFlag.PLAYER_STATS.value
            )
            insert_flag_stmt = insert_flag_stmt.on_conflict_do_update(
                index_elements=['code'],
                set_={
                    'sync_flags': MatchStatus.sync_flags.op('|')(MatchSyncFlag.PLAYER_STATS.value),
                    'update_at': func.now()
                }
            )
            session.execute(insert_flag_stmt)
            self.logger.info(f"Mark match {match_tag} players stats as synced")
