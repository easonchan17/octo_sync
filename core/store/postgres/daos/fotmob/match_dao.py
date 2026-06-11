import traceback
from sqlalchemy import func, and_, or_
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.dialects.postgresql import insert
from core.store.postgres.models.fotmob.fixture import Fixture, HistoryFixtureRaw, ActiveFixtureRaw
from core.store.postgres.models.fotmob.match import MatchRaw, MatchLineup, MatchStat, MatchPlayerStat, ShotStat, MatchPrediction
from core.store.postgres.models.common.league import SiteLeague
from core.types.enums import MatchStatus, SiteName
from ..base_dao import BaseDao

class MatchDao(BaseDao):
    def get_pending_fetch_items(self, kickoff_before: datetime, league_ids: List[int], limit: int) -> List[Any]:
        with self.db.get_session() as session:
            return session.query(
                Fixture.match_id,
                Fixture.kickoff_time,
                Fixture.page_url,
                Fixture.league_id,
                Fixture.league_name,
                func.coalesce(MatchRaw.fetch_attempts, 0).label("fetch_attempts")
            ).outerjoin(
                MatchRaw, Fixture.match_id == MatchRaw.match_id
            ).filter(
                Fixture.kickoff_time < kickoff_before,
                Fixture.league_id.in_(league_ids),
                ~Fixture.match_status.in_([MatchStatus.POSTPONED.value, MatchStatus.CANCELLED.value]),
                or_(
                    MatchRaw.match_id.is_(None),
                    MatchRaw.next_fetch_at <= func.now()
                )
            ).order_by(
                Fixture.kickoff_time.desc()
            ).limit(limit).all()

    def get_pending_parse_items(self, max_retries: int, limit: int) -> List[Any]:
        with self.db.get_session() as session:
            return session.query(
                MatchRaw.match_id,
                MatchRaw.kickoff_time,
                MatchRaw.json_body,
            ).join(
                Fixture, Fixture.match_id == MatchRaw.match_id
            ).filter(
                MatchRaw.is_fetched == True,
                MatchRaw.is_parsed == False,
                MatchRaw.parse_attempts < max_retries
            ).order_by(
                MatchRaw.created_at.asc()
            ).limit(limit).all()

    def mark_as_not_modified(self, match_id: int, fetch_interval: Optional[timedelta]) -> None:
        with self.db.get_session() as session:
            session.query(MatchRaw).filter(
                MatchRaw.match_id == match_id
            ).update({
                MatchRaw.is_fetched: True,
                MatchRaw.last_fetch_error: None,
                MatchRaw.last_fetched_at: func.now(),
                MatchRaw.next_fetch_at: func.now() + fetch_interval if fetch_interval is not None else None,
                MatchRaw.total_fetch_count: MatchRaw.total_fetch_count + 1,
                MatchRaw.fetch_attempts: 0,
                MatchRaw.updated_at: func.now()
            }, synchronize_session=False)

    def mark_as_fetched(self, match_id: int, fetch_interval: Optional[timedelta]) -> None:
        with self.db.get_session() as session:
            session.query(MatchRaw).filter(
                MatchRaw.match_id == match_id
            ).update({
                MatchRaw.is_fetched: True,
                MatchRaw.last_fetch_error: None,
                MatchRaw.last_fetched_at: func.now(),
                MatchRaw.next_fetch_at: func.now() + fetch_interval if fetch_interval is not None else None,
                MatchRaw.fetch_attempts: 0,
                MatchRaw.total_fetch_count: MatchRaw.total_fetch_count + 1,
                MatchRaw.is_parsed: False,
                MatchRaw.last_parse_error: None,
                MatchRaw.parse_attempts: 0,
                MatchRaw.updated_at: func.now()
            }, synchronize_session=False)

    def mark_fetch_failed(self, match_id: int, kickoff_time: datetime, source_url: str, error_msg: str, fetch_interval: Optional[timedelta]) -> None:
        next_fetch_at = func.now() + fetch_interval if fetch_interval is not None else None
        with self.db.get_session() as session:
            insert_stmt = insert(MatchRaw).values(
                match_id=match_id,
                kickoff_time=kickoff_time,
                source_url=source_url,
                is_fetched=False,
                fetch_attempts=1,
                last_fetch_error=(error_msg or "")[:2000],
                total_fetch_count=1,
                next_fetch_at=next_fetch_at,
                json_body={}
            )

            upsert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[MatchRaw.match_id],
                set_={
                    MatchRaw.source_url: source_url,
                    MatchRaw.is_fetched: False,
                    MatchRaw.last_fetch_error: (error_msg or "")[:2000],
                    MatchRaw.fetch_attempts: MatchRaw.fetch_attempts + 1,
                    MatchRaw.total_fetch_count: MatchRaw.total_fetch_count + 1,
                    MatchRaw.next_fetch_at: next_fetch_at,
                    MatchRaw.updated_at: func.now()
                }
            )

            session.execute(upsert_stmt)

    def mark_as_parsed(self, match_id: int, kickoff_time: datetime, match_status: int) -> None:
        with self.db.get_session() as session:
            session.query(MatchRaw).filter(
                MatchRaw.match_id == match_id
            ).update({
                MatchRaw.kickoff_time: kickoff_time,
                MatchRaw.match_status: match_status,
                MatchRaw.is_parsed: True,
                MatchRaw.last_parse_error: None,
                MatchRaw.parse_attempts: 0,
                MatchRaw.total_parse_count: MatchRaw.total_parse_count + 1,
                MatchRaw.last_parsed_at: func.now(),
                MatchRaw.updated_at: func.now()
            }, synchronize_session=False)

    def mark_parse_failed(self, match_id: int, error_msg: Optional[str] = None) -> None:
        if error_msg is None:
            error_msg = traceback.format_exc()
        with self.db.get_session() as session:
            session.query(MatchRaw).filter(
                MatchRaw.match_id == match_id
            ).update({
                MatchRaw.is_parsed: False,
                MatchRaw.last_parse_error: error_msg[:2000],
                MatchRaw.parse_attempts: MatchRaw.parse_attempts + 1,
                MatchRaw.total_parse_count: MatchRaw.total_parse_count + 1,
                MatchRaw.updated_at: func.now()
            }, synchronize_session=False)

    def sync_raw_data(self, raw_data: Dict[str, Any]) -> None:
        with self.db.get_session() as session:
            insert_stmt = insert(MatchRaw).values(raw_data)

            update_values = {
                MatchRaw.source_url.key: raw_data["source_url"],
                MatchRaw.kickoff_time.key: raw_data["kickoff_time"],
                MatchRaw.json_body.key: raw_data["json_body"],
                MatchRaw.updated_at.key: func.now()
            }

            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[MatchRaw.match_id.key],
                set_=update_values
            )
            result = session.execute(insert_stmt)
            upserted_count = result.rowcount
            self.logger.debug(f"Sync match raw data completed. upserted: {upserted_count}")

    def sync_parsed_data(self, parsed_data: Dict[str, Any]) -> None:
        match_id = parsed_data.get("match_id")
        lineup = parsed_data.get("lineup")
        match_stats = parsed_data.get("match_stats")
        player_stats = parsed_data.get("player_stats")
        shot_stats = parsed_data.get('shot_stats')

        with self.db.get_session() as session:
            if lineup:
                session.query(MatchLineup).filter(MatchLineup.match_id == match_id).delete(synchronize_session=False)
                session.execute(insert(MatchLineup).values(lineup))
            if match_stats:
                session.query(MatchStat).filter(MatchStat.match_id == match_id).delete(synchronize_session=False)
                session.execute(insert(MatchStat).values(match_stats))
            if player_stats:
                session.query(MatchPlayerStat).filter(MatchPlayerStat.match_id == match_id).delete(synchronize_session=False)
                session.execute(insert(MatchPlayerStat).values(player_stats))
            if shot_stats:
                session.query(ShotStat).filter(ShotStat.match_id == match_id).delete(synchronize_session=False)
                session.execute(insert(ShotStat).values(shot_stats))

    def get_match_detail(self, match_code: str) -> Dict[str, Any]:
        with self.db.get_session() as session:
            row = session.query(
                Fixture.match_id,
                Fixture.match_code,
                Fixture.league_id,
                Fixture.kickoff_time,
                Fixture.round,
                Fixture.group_name,
                Fixture.home_id,
                Fixture.home_team,
                Fixture.home_code,
                Fixture.away_id,
                Fixture.away_team,
                Fixture.away_code,
                Fixture.home_score,
                Fixture.away_score,
                Fixture.home_pen_score,
                Fixture.away_pen_score,
                Fixture.match_status,
                MatchRaw.json_body.label('match_json_body'),
                HistoryFixtureRaw.json_body.label('standings_json_body'),
            ).outerjoin(
                MatchRaw, MatchRaw.match_id == Fixture.match_id
            ).outerjoin(
                HistoryFixtureRaw,
                and_(
                    HistoryFixtureRaw.league_id == Fixture.league_id,
                    HistoryFixtureRaw.season == Fixture.season,
                )
            ).filter(Fixture.match_code == match_code).first()

            if not row:
                raise ValueError("Match not found")

            return row._asdict()

    def get_match_shot_map(self, match_id: int) -> List[Dict[str, Any]]:
        with self.db.get_session() as session:
            rows = session.query(
                ShotStat.x,
                ShotStat.y,
                ShotStat.min,
                ShotStat.min_added,
                ShotStat.period,
                ShotStat.player_name,
                ShotStat.shot_type,
                ShotStat.event_type,
                ShotStat.situation,
                ShotStat.is_on_target,
                ShotStat.is_blocked,
                ShotStat.is_own_goal,
                ShotStat.xg,
                ShotStat.xgot,
                ShotStat.on_goal_shot_x,
                ShotStat.on_goal_shot_y,
                ShotStat.goal_y,
                ShotStat.goal_z,
                ShotStat.team_code,
                ShotStat.player_code,
            ).filter(ShotStat.match_id == match_id).order_by(ShotStat.min.asc()).all()
            return [row._asdict() for row in rows]

    def get_team_lineup(self, match_id: int, team_id: int) -> List[Dict[str, Any]]:
        with self.db.get_session() as session:
            rows = session.query(
                MatchLineup.team_id,
                MatchLineup.team_name,
                MatchLineup.player_id,
                MatchLineup.player_name,
                MatchLineup.player_code,
                MatchLineup.shirt_number,
                MatchLineup.position,
                MatchLineup.usual_playing_position_id,
                MatchLineup.role,
                MatchLineup.is_captain,
                MatchLineup.rating,
            ).filter(
                MatchLineup.match_id == match_id,
                MatchLineup.team_id == team_id,
            ).all()
            return [row._asdict() for row in rows]

    def get_match_lineup(self, match_code: str) -> List[Dict[str, Any]]:
        with self.db.get_session() as session:
            rows = session.query(
                MatchLineup.team_name,
                MatchLineup.player_name,
                MatchLineup.position,
                MatchLineup.usual_playing_position_id,
                MatchLineup.role,
                MatchLineup.is_captain,
            ).join(
                Fixture, Fixture.match_id == MatchLineup.match_id
            ).filter(
                Fixture.match_code == match_code,
            ).order_by(
                MatchLineup.team_name, MatchLineup.role, MatchLineup.shirt_number
            ).all()
            return [row._asdict() for row in rows]

    def get_match_stats(self, match_id: int) -> Optional[Dict[str, Any]]:
        with self.db.get_session() as session:
            row = session.query(
                MatchStat.lineup_type,
                MatchStat.home_formation,
                MatchStat.away_formation,
                MatchStat.home_possession,
                MatchStat.away_possession,
                MatchStat.home_goals_penalty,
                MatchStat.away_goals_penalty,
                MatchStat.home_shots,
                MatchStat.away_shots,
                MatchStat.home_shots_on_target,
                MatchStat.away_shots_on_target,
                MatchStat.home_shots_off_target,
                MatchStat.away_shots_off_target,
                MatchStat.home_hit_woodwork,
                MatchStat.away_hit_woodwork,
                MatchStat.home_shots_inside_box,
                MatchStat.away_shots_inside_box,
                MatchStat.home_shots_outside_box,
                MatchStat.away_shots_outside_box,
                MatchStat.home_big_chances,
                MatchStat.away_big_chances,
                MatchStat.home_big_chances_missed,
                MatchStat.away_big_chances_missed,
                MatchStat.home_xg,
                MatchStat.away_xg,
                MatchStat.home_xg_open_play,
                MatchStat.away_xg_open_play,
                MatchStat.home_xg_set_play,
                MatchStat.away_xg_set_play,
                MatchStat.home_npxg,
                MatchStat.away_npxg,
                MatchStat.home_xg_on_target,
                MatchStat.away_xg_on_target,
                MatchStat.home_passes,
                MatchStat.away_passes,
                MatchStat.home_passes_completed,
                MatchStat.away_passes_completed,
                MatchStat.home_own_half_passes,
                MatchStat.away_own_half_passes,
                MatchStat.home_opp_half_passes,
                MatchStat.away_opp_half_passes,
                MatchStat.home_long_passes,
                MatchStat.away_long_passes,
                MatchStat.home_long_passes_completed,
                MatchStat.away_long_passes_completed,
                MatchStat.home_crosses,
                MatchStat.away_crosses,
                MatchStat.home_crosses_completed,
                MatchStat.away_crosses_completed,
                MatchStat.home_throws,
                MatchStat.away_throws,
                MatchStat.home_corners,
                MatchStat.away_corners,
                MatchStat.home_tackles,
                MatchStat.away_tackles,
                MatchStat.home_interceptions,
                MatchStat.away_interceptions,
                MatchStat.home_shot_blocks,
                MatchStat.away_shot_blocks,
                MatchStat.home_clearances,
                MatchStat.away_clearances,
                MatchStat.home_keeper_saves,
                MatchStat.away_keeper_saves,
                MatchStat.home_duels_won,
                MatchStat.away_duels_won,
                MatchStat.home_ground_duels,
                MatchStat.away_ground_duels,
                MatchStat.home_ground_duels_won,
                MatchStat.away_ground_duels_won,
                MatchStat.home_aerials,
                MatchStat.away_aerials,
                MatchStat.home_aerials_won,
                MatchStat.away_aerials_won,
                MatchStat.home_dribbles,
                MatchStat.away_dribbles,
                MatchStat.home_dribbles_completed,
                MatchStat.away_dribbles_completed,
                MatchStat.home_fouls_committed,
                MatchStat.away_fouls_committed,
                MatchStat.home_yellow_cards,
                MatchStat.away_yellow_cards,
                MatchStat.home_red_cards,
                MatchStat.away_red_cards,
            ).filter(MatchStat.match_id == match_id).first()
            return row._asdict() if row else None

    def get_team_h2h(self, home_id: int, away_id: int, min_kickoff_time: datetime, max_kickoff_time: datetime) -> List[Dict[str, Any]]:
        with self.db.get_session() as session:
            rows = session.query(
                SiteLeague.ref_league_id,
                Fixture.match_code,
                Fixture.kickoff_time,
                Fixture.league_id,
                Fixture.league_name,
                Fixture.home_team,
                Fixture.home_code,
                Fixture.home_score,
                Fixture.away_team,
                Fixture.away_code,
                Fixture.away_score,
                Fixture.match_status,
            ).join(
                SiteLeague,
                and_(
                    SiteLeague.league_id == Fixture.league_id,
                    SiteLeague.site_name == SiteName.FOTMOB.value
                )
            ).filter(
                or_(
                    and_(Fixture.home_id == home_id, Fixture.away_id == away_id),
                    and_(Fixture.home_id == away_id, Fixture.away_id == home_id),
                ),
                Fixture.kickoff_time >= min_kickoff_time,
                Fixture.kickoff_time < max_kickoff_time,
                Fixture.match_status.in_(MatchStatus.natural_finals())
            ).order_by(Fixture.kickoff_time.desc()).all()
            return [row._asdict() for row in rows]

    def get_team_form(self, team_id: int, max_kickoff_time: datetime, limit: int) -> List[Dict[str, Any]]:
        with self.db.get_session() as session:
            rows = session.query(
                SiteLeague.ref_league_id,
                Fixture.match_code,
                Fixture.kickoff_time,
                Fixture.league_id,
                Fixture.league_name,
                Fixture.home_team,
                Fixture.home_code,
                Fixture.home_score,
                Fixture.away_team,
                Fixture.away_code,
                Fixture.away_score,
                Fixture.match_status,
            ).join(
                SiteLeague,
                and_(
                    SiteLeague.league_id == Fixture.league_id,
                    SiteLeague.site_name == SiteName.FOTMOB.value
                )
            ).filter(
                or_(Fixture.home_id == team_id, Fixture.away_id == team_id),
                Fixture.kickoff_time < max_kickoff_time,
                Fixture.match_status.in_(MatchStatus.natural_finals())
            ).order_by(Fixture.kickoff_time.desc()).limit(limit).all()
            return [row._asdict() for row in rows]

    def get_prediction(self, match_code: str, model_version: str) -> Optional[Any]:
        with self.db.get_session() as session:
            return session.query(
                MatchPrediction.model_version,
                MatchPrediction.home_prob,
                MatchPrediction.draw_prob,
                MatchPrediction.away_prob,
                MatchPrediction.prediction,
            ).filter(
                MatchPrediction.match_code == match_code,
                MatchPrediction.model_version == model_version,
            ).first()

    def get_latest_prediction(self, match_code: str) -> Optional[Any]:
        with self.db.get_session() as session:
            return session.query(
                MatchPrediction.model_version,
                MatchPrediction.home_prob,
                MatchPrediction.draw_prob,
                MatchPrediction.away_prob,
                MatchPrediction.prediction,
                MatchPrediction.certainty,
                MatchPrediction.predicted_at,
            ).filter(
                MatchPrediction.match_code == match_code,
            ).order_by(MatchPrediction.predicted_at.desc()).first()

    def get_pending_predict_items(self, model_version: str, league_ids: List[int], min_kickoff_time: datetime, max_kickoff_time: datetime) -> List[Any]:
        with self.db.get_session() as session:
            return session.query(
                Fixture.match_code,
                Fixture.kickoff_time,
            ).outerjoin(
                MatchPrediction,
                and_(
                    MatchPrediction.match_code == Fixture.match_code,
                    MatchPrediction.model_version == model_version
                )
            ).filter(
                Fixture.kickoff_time >= min_kickoff_time,
                Fixture.kickoff_time <= max_kickoff_time,
                Fixture.league_id.in_(league_ids),
                Fixture.match_status == MatchStatus.TIMED.value,
                or_(
                    MatchPrediction.match_code.is_(None),
                    MatchPrediction.next_predict_at <= func.now()
                )
            ).order_by(Fixture.kickoff_time.asc()).all()

    def reschedule_prediction(self, match_code: str, model_version: str, interval: Optional[timedelta]) -> None:
        next_predict_at = func.now() + interval if interval is not None else None
        with self.db.get_session() as session:
            session.query(MatchPrediction).filter(
                MatchPrediction.match_code == match_code,
                MatchPrediction.model_version == model_version,
            ).update({
                MatchPrediction.next_predict_at: next_predict_at,
                MatchPrediction.updated_at: func.now(),
            }, synchronize_session=False)

    def sync_predict_data(self, data: Dict[str, Any]) -> None:
        with self.db.get_session() as session:
            stmt = insert(MatchPrediction).values(data)
            stmt = stmt.on_conflict_do_update(
                index_elements=[MatchPrediction.match_code, MatchPrediction.model_version],
                set_={
                    MatchPrediction.home_prob.key: stmt.excluded.home_prob,
                    MatchPrediction.draw_prob.key: stmt.excluded.draw_prob,
                    MatchPrediction.away_prob.key: stmt.excluded.away_prob,
                    MatchPrediction.prediction.key: stmt.excluded.prediction,
                    MatchPrediction.predicted_at.key: stmt.excluded.predicted_at,
                    MatchPrediction.certainty.key: stmt.excluded.certainty,
                    MatchPrediction.updated_at.key: func.now(),
                }
            )
            session.execute(stmt)