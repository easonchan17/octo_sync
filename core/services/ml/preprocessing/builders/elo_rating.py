import numpy as np
import pandas as pd
from typing import Any, Optional, Dict
from sqlalchemy.orm import aliased
from core.types.enums import MatchStatus
from core.types.params import EloParams
from core.store.postgres.models.fotmob import Fixture, EloRating

from .base import BaseFeatureBuilder

class EloRatingFeatureBuilder(BaseFeatureBuilder):
    def _build(self, df: pd.DataFrame) -> pd.DataFrame:
        base_rating = self.elo_params.base_rating
        home_advantage = self.elo_params.home_advantage
        min_games_for_stability = self.elo_params.min_games_for_stability

        home_trust_factor = ((df['home_game_count'] - 1) / min_games_for_stability).clip(upper=1.0)
        home_elo_rating_series = df['home_pre_rating'] * home_trust_factor + base_rating * (1 - home_trust_factor)

        away_trust_factor = ((df['away_game_count'] - 1) / min_games_for_stability).clip(upper=1.0)
        away_elo_rating_series = df['away_pre_rating'] * away_trust_factor + base_rating * (1 - away_trust_factor)

        elo_rating_diff_series = home_elo_rating_series - away_elo_rating_series
        home_net_advantage_series = elo_rating_diff_series + home_advantage
        match_balance_series = 0.1 + 0.9 * np.exp(-1 * (home_net_advantage_series / 400) ** 2)
        home_expected_score_series = (1 / (1 + 10 ** (-home_net_advantage_series / 400))).clip(0.01, 0.99)

        df['home_elo_rating'] = home_elo_rating_series
        df['away_elo_rating'] = away_elo_rating_series
        df['home_net_advantage'] = home_net_advantage_series
        df['home_elo_expectancy'] = home_expected_score_series
        df['match_balance'] = match_balance_series

        self.logger.info("Built ELO rating features")

        return df[['match_id', 'home_elo_rating', 'away_elo_rating', 'home_net_advantage', 'home_elo_expectancy', 'match_balance']]


class EloRatingTrainFeatureBuilder(EloRatingFeatureBuilder):
    def __init__(self, league_ids: list, min_season: int, max_season: int, elo_params: EloParams = EloParams()) -> None:
        super().__init__()
        self.league_ids = league_ids
        self.min_season = min_season
        self.max_season = max_season
        self.elo_params = elo_params

    def _load(self) -> Optional[pd.DataFrame]:
        with self.db.get_session() as session:
            HomeElo = aliased(EloRating)
            AwayElo = aliased(EloRating)

            results = session.query(Fixture, HomeElo, AwayElo).outerjoin(
                HomeElo, (HomeElo.match_id == Fixture.match_id) & (HomeElo.team_id == Fixture.home_id)
            ).outerjoin(
                AwayElo, (AwayElo.match_id == Fixture.match_id) & (AwayElo.team_id == Fixture.away_id)
            ).filter(
                Fixture.league_id.in_(self.league_ids),
                Fixture.season >= self.min_season,
                Fixture.season <= self.max_season,
                Fixture.match_status.in_(MatchStatus.natural_finals())
            ).order_by(Fixture.kickoff_time).all()

            records = []
            for fixture, home_elo, away_elo in results:
                record = {"match_id": fixture.match_id}
                if home_elo:
                    record.update({
                        "home_pre_rating": float(home_elo.pre_rating),
                        "home_game_count": home_elo.game_count,
                    })
                if away_elo:
                    record.update({
                        "away_pre_rating": float(away_elo.pre_rating),
                        "away_game_count": away_elo.game_count,
                    })
                records.append(record)

            return pd.DataFrame(records) if records else None


class EloRatingPredictFeatureBuilder(EloRatingFeatureBuilder):
    def __init__(self, fixture: Any, elo_params: EloParams = EloParams()) -> None:
        super().__init__()
        self.match_id = fixture.match_id
        self.home_id  = fixture.home_id
        self.away_id  = fixture.away_id
        self.elo_params = elo_params

    def _load(self) -> Optional[pd.DataFrame]:
        with self.db.get_session() as session:
            elo_results = (
                session.query(EloRating.team_id, EloRating.post_rating, EloRating.game_count)
                .filter(EloRating.team_id.in_([self.home_id, self.away_id]))
                .distinct(EloRating.team_id)
                .order_by(EloRating.team_id, EloRating.game_count.desc())
                .all()
            )

        base_rating = self.elo_params.base_rating
        record = {
            "match_id":        self.match_id,
            "home_pre_rating": base_rating,
            "home_game_count": 0,
            "away_pre_rating": base_rating,
            "away_game_count": 0,
        }
        for team_id, post_rating, game_count in elo_results:
            if team_id == self.home_id:
                record.update({"home_pre_rating": float(post_rating), "home_game_count": game_count + 1})
            elif team_id == self.away_id:
                record.update({"away_pre_rating": float(post_rating), "away_game_count": game_count + 1})

        return pd.DataFrame([record])

    def _build(self, df: pd.DataFrame) -> Dict[str, Any]:
        df = super()._build(df)

        row = df.iloc[0].to_dict()
        row.pop("match_id", None)
        return row
