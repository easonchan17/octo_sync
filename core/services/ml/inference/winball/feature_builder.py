import numpy as np
import pandas as pd
from sqlalchemy import desc
from datetime import datetime
from typing import Dict, Any, Optional
from core.types.params import EloParams
from core.logger.logger_manager import LoggerManager
from core.store.postgres.models import FotmobFixture, EloRating
from core.services.ml.preprocessing.builders.feature.odds import OddsFeatureBuilder
from core.services.ml.preprocessing.transforms import FormulaMutator, EntropyMutator
from core.store.postgres.postgresql_manager import PostgreSQLManager
from core.services.ml.preprocessing import PredictSampleBuilder


class FeatureBuilder:
    def __init__(self) -> None:
        self.logger = LoggerManager.get_instance().get_logger(self.__class__.__name__)
        self.db = PostgreSQLManager.get_instance()

    def build(self, fixture_id: int) -> Dict[str, Any]:
        fixture_info = self._get_fotmob_fixture(fixture_id)
        if not fixture_info:
            raise ValueError(f"Fixture with id {fixture_id} not found")

        home_id = fixture_info['home_id']
        away_id = fixture_info['away_id']
        match_id = fixture_info['match_id']
        kickoff_time = fixture_info['kickoff_time']
        self.logger.info(f"Building sample for fixture_id={fixture_id}, match_id={match_id}")

        aggregator = PredictSampleBuilder(home_id, away_id, kickoff_time)
        aggregated_df = aggregator.execute()
        if aggregated_df is None or aggregated_df.empty:
            raise ValueError(f"No aggregated data for home_id={home_id} vs away_id={away_id}")

        result = aggregated_df.iloc[-1].to_dict()

        market_odds = self._get_pinnacle_odds(match_id)
        elo_rating = self._get_elo_rating(home_id, away_id, kickoff_time)

        derived_features = self._derive_features(market_odds, elo_rating)
        result.update(derived_features)

        self._log_sample(result)

        return result

    def _log_sample(self, sample: Dict[str, Any]) -> None:
        lines = ["\n" + "=" * 60, "Prediction Sample Features", "=" * 60]
        for key, value in sorted(sample.items()):
            if isinstance(value, float):
                lines.append(f"  {key:<40}: {value:>12.4f}")
            else:
                lines.append(f"  {key:<40}: {str(value):>12}")
        lines.append("=" * 60)
        self.logger.info("\n".join(lines))

    def _derive_features(self, market_odds: Dict[str, Any], elo_rating: Dict[str, Any]) -> Dict[str, Any]:
        df = pd.DataFrame([{**market_odds, **elo_rating}])

        FormulaMutator(df).mutate_batch(OddsFeatureBuilder.ODDS_FEATURES)
        EntropyMutator(df).mutate("entropy_1x2_open", ['home_open_real', 'draw_open_real', 'away_open_real'])
        EntropyMutator(df).mutate("entropy_1x2_close", ['home_close_real', 'draw_close_real', 'away_close_real'])
        self._derive_elo_features(df)

        return df.iloc[0].to_dict()

    def _derive_elo_features(self, df: pd.DataFrame) -> None:
        elo_params = EloParams()

        home_trust = ((df['home_game_count'] - 1) / elo_params.min_games_for_stability).clip(upper=1.0)
        home_elo = df['home_pre_rating'] * home_trust + elo_params.base_rating * (1 - home_trust)

        away_trust = ((df['away_game_count'] - 1) / elo_params.min_games_for_stability).clip(upper=1.0)
        away_elo = df['away_pre_rating'] * away_trust + elo_params.base_rating * (1 - away_trust)

        elo_diff = home_elo - away_elo
        net_advantage = elo_diff + elo_params.home_advantage

        df['home_elo_rating'] = home_elo
        df['away_elo_rating'] = away_elo
        df['elo_rating_diff'] = elo_diff
        df['home_net_advantage'] = net_advantage
        df['home_elo_expectancy'] = (1 / (1 + 10 ** (-net_advantage / 400))).clip(0.01, 0.99)
        df['match_balance'] = 0.1 + 0.9 * np.exp(-1 * (net_advantage / 400) ** 2)

    def _get_fotmob_fixture(self, fixture_id: int) -> Optional[Dict[str, Any]]:
        with self.db.get_session() as session:
            fixture = session.query(FotmobFixture).filter(
                FotmobFixture.id == fixture_id
            ).first()

            if not fixture:
                return None

            return {
                'match_id': fixture.match_id,
                'kickoff_time': fixture.kickoff_time,
                'home_id': fixture.home_id,
                'home_team': fixture.home_team,
                'away_id': fixture.away_id,
                'away_team': fixture.away_team
            }

    def _get_pinnacle_odds(self, fixture_id: int) -> Dict[str, Any]:
        with self.db.get_session() as session:
            fixture = session.query(PinnacleFixture.match_id).filter(
                PinnacleFixture.fixture_id == fixture_id
            ).first()

            if not fixture:
                raise ValueError(f"No Pinnacle fixture found for match_id={fixture_id}")

            match_id = fixture[0]

            earliest_moneyline = session.query(
                Moneyline.home_odds, Moneyline.draw_odds, Moneyline.away_odds
            ).filter(
                Moneyline.match_id == match_id,
                Moneyline.period == 0
            ).order_by(Moneyline.created_at).first()

            latest_moneyline = session.query(
                Moneyline.home_odds, Moneyline.draw_odds, Moneyline.away_odds
            ).filter(
                Moneyline.match_id == match_id,
                Moneyline.period == 0
            ).order_by(desc(Moneyline.created_at)).first()

            earliest_spread = session.query(
                Spread.handicap, Spread.home_odds, Spread.away_odds
            ).filter(
                Spread.match_id == match_id,
                Spread.period == 0,
                Spread.is_alternate == False
            ).order_by(Spread.created_at).first()

            latest_spread = session.query(
                Spread.handicap, Spread.home_odds, Spread.away_odds
            ).filter(
                Spread.match_id == match_id,
                Spread.period == 0,
                Spread.is_alternate == False
            ).order_by(desc(Spread.created_at)).first()

            if not earliest_moneyline or not latest_moneyline or not earliest_spread or not latest_spread:
                raise ValueError(f"Incomplete odds data for match_id={fixture_id}")

            return {
                'home_open_odds': float(earliest_moneyline[0]),
                'draw_open_odds': float(earliest_moneyline[1]),
                'away_open_odds': float(earliest_moneyline[2]),
                'home_close_odds': float(latest_moneyline[0]),
                'draw_close_odds': float(latest_moneyline[1]),
                'away_close_odds': float(latest_moneyline[2]),
                'ah_line_open': float(earliest_spread[0]),
                'ah_home_open_odds': float(earliest_spread[1]),
                'ah_away_open_odds': float(earliest_spread[2]),
                'ah_line_close': float(latest_spread[0]),
                'ah_home_close_odds': float(latest_spread[1]),
                'ah_away_close_odds': float(latest_spread[2])
            }

    def _get_elo_rating(self, home_id: int, away_id: int, kickoff_time: datetime) -> Dict[str, Any]:
        elo_params = EloParams()
        with self.db.get_session() as session:
            home_elo = session.query(EloRating).filter(
                EloRating.team_id == home_id,
                EloRating.kickoff_time < kickoff_time
            ).order_by(EloRating.kickoff_time.desc()).first()

            away_elo = session.query(EloRating).filter(
                EloRating.team_id == away_id,
                EloRating.kickoff_time < kickoff_time
            ).order_by(EloRating.kickoff_time.desc()).first()

            result = {}
            if home_elo:
                result.update({
                    "home_pre_rating": float(home_elo.post_rating),
                    "home_game_count": home_elo.game_count + 1
                })
            else:
                result.update({
                    "home_pre_rating": elo_params.base_rating,
                    "home_game_count": 1
                })

            if away_elo:
                result.update({
                    "away_pre_rating": float(away_elo.post_rating),
                    "away_game_count": away_elo.game_count + 1
                })
            else:
                result.update({
                    "away_pre_rating": elo_params.base_rating,
                    "away_game_count": 1
                })

            return result
