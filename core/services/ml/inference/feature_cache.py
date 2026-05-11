from functools import lru_cache
from datetime import datetime
from typing import Dict, Optional
from core.logger.logger_manager import LoggerManager
from core.services.ml.preprocessing.builders.feature.match import MatchLatestFeatureBuilder
from core.services.ml.preprocessing.builders.feature.player import OutfieldPlayerLatestFeatureBuilder, GoalkeeperLatestFeatureBuilder


class FeatureCache:
    def __init__(self) -> None:
        self.logger = LoggerManager.get_instance().get_logger(self.__class__.__name__)
        self._team_stats:   Dict[int, Dict] = {}
        self._player_stats: Dict[int, Dict] = {}
        self._gk_stats:     Dict[int, Dict] = {}

    def rebuild(self, min_kickoff_time: datetime) -> None:
        team_df   = MatchLatestFeatureBuilder(min_kickoff_time).build()
        player_df = OutfieldPlayerLatestFeatureBuilder(min_kickoff_time).build()
        gk_df     = GoalkeeperLatestFeatureBuilder(min_kickoff_time).build()

        self._team_stats = (
            team_df.sort_values("kickoff_time").groupby("team_id").last().to_dict("index")
            if team_df is not None else {}
        )
        self._player_stats = (
            player_df.sort_values("kickoff_time").groupby("player_id").last().to_dict("index")
            if player_df is not None else {}
        )
        self._gk_stats = (
            gk_df.sort_values("kickoff_time").groupby("player_id").last().to_dict("index")
            if gk_df is not None else {}
        )
        self.logger.info(
            f"FeatureCache rebuilt: {len(self._team_stats)} teams, "
            f"{len(self._player_stats)} outfield players, {len(self._gk_stats)} goalkeepers"
        )

    def get_team_state(self, team_id: int) -> Optional[Dict]:
        return self._team_stats.get(team_id)

    def get_player_state(self, player_id: int) -> Optional[Dict]:
        return self._player_stats.get(player_id)

    def get_gk_state(self, player_id: int) -> Optional[Dict]:
        return self._gk_stats.get(player_id)


@lru_cache(maxsize=1)
def get_feature_cache() -> FeatureCache:
    return FeatureCache()


feature_cache = get_feature_cache()
