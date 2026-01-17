from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import func, and_, or_
from sqlalchemy.orm import aliased, Session
from core.store.postgres.models import (
    Site, EloRating, MatchFixture, MatchResult,
    GoalAndShotCreation, Passing, Shooting, DefensiveAction,
    GoalKeeping, MarketOdds, Status
)
from ..base_synchronizer import BaseSynchronizer
import pandas as pd


class EloRatingSynchronizer(BaseSynchronizer):
    def sync(
        self,
        site: Site,
        elo_ratings: List[Dict[str, Any]]
    ) -> None:
        if not elo_ratings:
            self.logger.warning(f"No elo ratings to sync from {site.name}")
            return

        with self.db.get_session(site.get_namespace()) as session:
            insert_stmt = insert(EloRating).values(elo_ratings)
            assignment, where_clause = self.build_upsert_clauses(
                EloRating,
                insert_stmt,
                {
                    EloRating.id.key,
                    EloRating.created_at.key,
                    EloRating.match_code.key,
                    EloRating.team_code.key,
                    EloRating.updated_at.key
                }
            )

            insert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=[EloRating.team_code.key, EloRating.match_code.key],
                set_=assignment,
                where=where_clause
            )
            result = session.execute(insert_stmt)
            upserted_count = result.rowcount
            self.logger.info(f"Sync elo ratings from {site.name} completed. upserted: {upserted_count}")

    def get_fixture(self, site: Site, fixture_id: int) -> Optional[MatchFixture]:
        with self.db.get_session(site.get_namespace()) as session:
            fixture = session.query(MatchFixture).filter(
                MatchFixture.id == fixture_id,
                MatchFixture.status.op('&')(Status.ACTIVE.value) == Status.ACTIVE.value
            ).first()

            if fixture:
                session.expunge(fixture)
            return fixture

    def query_match_stats_for_prediction(
        self,
        site: Site,
        fixture: MatchFixture,
        max_matches_per_team: int = 30
    ) -> List[Tuple]:
        with self.db.get_session(site.get_namespace()) as session:
            gca_home = aliased(GoalAndShotCreation)
            gca_away = aliased(GoalAndShotCreation)
            passing_home = aliased(Passing)
            passing_away = aliased(Passing)
            shooting_home = aliased(Shooting)
            shooting_away = aliased(Shooting)
            defensive_home = aliased(DefensiveAction)
            defensive_away = aliased(DefensiveAction)
            goalkeeping_home = aliased(GoalKeeping)
            goalkeeping_away = aliased(GoalKeeping)
            market_odds = aliased(MarketOdds)

            base_query = session.query(
                MatchResult,
                gca_home,
                gca_away,
                passing_home,
                passing_away,
                shooting_home,
                shooting_away,
                defensive_home,
                defensive_away,
                goalkeeping_home,
                goalkeeping_away,
                market_odds
            ).outerjoin(
                gca_home,
                and_(
                    MatchResult.match_code == gca_home.match_code,
                    MatchResult.home_code == gca_home.team_code
                )
            ).outerjoin(
                gca_away,
                and_(
                    MatchResult.match_code == gca_away.match_code,
                    MatchResult.away_code == gca_away.team_code
                )
            ).outerjoin(
                passing_home,
                and_(
                    MatchResult.match_code == passing_home.match_code,
                    MatchResult.home_code == passing_home.team_code
                )
            ).outerjoin(
                passing_away,
                and_(
                    MatchResult.match_code == passing_away.match_code,
                    MatchResult.away_code == passing_away.team_code
                )
            ).outerjoin(
                shooting_home,
                and_(
                    MatchResult.match_code == shooting_home.match_code,
                    MatchResult.home_code == shooting_home.team_code
                )
            ).outerjoin(
                shooting_away,
                and_(
                    MatchResult.match_code == shooting_away.match_code,
                    MatchResult.away_code == shooting_away.team_code
                )
            ).outerjoin(
                defensive_home,
                and_(
                    MatchResult.match_code == defensive_home.match_code,
                    MatchResult.home_code == defensive_home.team_code
                )
            ).outerjoin(
                defensive_away,
                and_(
                    MatchResult.match_code == defensive_away.match_code,
                    MatchResult.away_code == defensive_away.team_code
                )
            ).outerjoin(
                goalkeeping_home,
                and_(
                    MatchResult.match_code == goalkeeping_home.match_code,
                    MatchResult.home_code == goalkeeping_home.team_code
                )
            ).outerjoin(
                goalkeeping_away,
                and_(
                    MatchResult.match_code == goalkeeping_away.match_code,
                    MatchResult.away_code == goalkeeping_away.team_code
                )
            ).outerjoin(
                market_odds,
                MatchResult.match_code == market_odds.match_code
            ).filter(
                MatchResult.comp_code == fixture.comp_code,
                MatchResult.season == fixture.season,
                MatchResult.kickoff_time < fixture.kickoff_time,
                MatchResult.status.op('&')(Status.ACTIVE.value) == Status.ACTIVE.value
            )

            home_team_matches = base_query.filter(
                or_(
                    MatchResult.home_code == fixture.home_code,
                    MatchResult.away_code == fixture.home_code
                )
            ).order_by(MatchResult.kickoff_time.desc()).limit(max_matches_per_team).all()

            away_team_matches = base_query.filter(
                or_(
                    MatchResult.home_code == fixture.away_code,
                    MatchResult.away_code == fixture.away_code
                )
            ).order_by(MatchResult.kickoff_time.desc()).limit(max_matches_per_team).all()

            h2h_matches = base_query.filter(
                and_(
                    or_(
                        MatchResult.home_code == fixture.home_code,
                        MatchResult.away_code == fixture.home_code
                    ),
                    or_(
                        MatchResult.home_code == fixture.away_code,
                        MatchResult.away_code == fixture.away_code
                    )
                )
            ).order_by(MatchResult.kickoff_time.desc()).all()

            match_codes = set()
            for row in home_team_matches:
                match_codes.add(row[0].match_code)
            for row in away_team_matches:
                match_codes.add(row[0].match_code)
            for row in h2h_matches:
                match_codes.add(row[0].match_code)

            self.logger.info(
                f"Query match stats for fixture {fixture.id}: "
                f"home_team_matches={len(home_team_matches)}, "
                f"away_team_matches={len(away_team_matches)}, "
                f"h2h_matches={len(h2h_matches)}, "
                f"unique_match_codes={len(match_codes)}"
            )

            all_matches_query = base_query.filter(
                MatchResult.match_code.in_(match_codes)
            ).order_by(MatchResult.kickoff_time.asc())

            results = all_matches_query.all()

            if results:
                session.expunge_all()

            return results

    def get_match_results(
        self,
        site: Site,
        comp_code: str,
        min_season: int,
        max_season: int,
        is_force: bool = False
    ) -> List[MatchResult]:
        with self.db.get_session(site.get_namespace()) as session:
            query = session.query(MatchResult).filter(
                MatchResult.comp_code == comp_code,
                MatchResult.season >= min_season,
                MatchResult.season <= max_season,
                MatchResult.home_gf.isnot(None),
                MatchResult.away_gf.isnot(None)
            ).order_by(MatchResult.kickoff_time.asc())

            if not is_force:
                existing_match_codes_subquery = session.query(EloRating.match_code).distinct()
                query = query.filter(~MatchResult.match_code.in_(existing_match_codes_subquery))

            results = query.all()

            if results:
                session.expunge_all()

            return results

    def get_existing_elo_ratings(self, site: Site) -> Tuple[Dict[str, float], Dict[str, int], Dict[str, int]]:
        with self.db.get_session(site.get_namespace()) as session:
            latest_ratings_subquery = session.query(
                EloRating.team_code,
                func.max(EloRating.kickoff_time).label('max_time')
            ).group_by(EloRating.team_code).subquery()

            latest_ratings_query = session.query(EloRating).join(
                latest_ratings_subquery,
                and_(
                    EloRating.team_code == latest_ratings_subquery.c.team_code,
                    EloRating.kickoff_time == latest_ratings_subquery.c.max_time
                )
            )

            existing_ratings = {}
            existing_last_seasons = {}

            for rating_record in latest_ratings_query.all():
                team_code = rating_record.team_code
                existing_ratings[team_code] = float(rating_record.post_rating)
                existing_last_seasons[team_code] = rating_record.season

            game_counts_query = session.query(
                EloRating.team_code,
                func.count(EloRating.id).label('count')
            ).group_by(EloRating.team_code)

            existing_game_counts = {}
            for count_record in game_counts_query.all():
                existing_game_counts[count_record.team_code] = count_record.count

            return existing_ratings, existing_last_seasons, existing_game_counts