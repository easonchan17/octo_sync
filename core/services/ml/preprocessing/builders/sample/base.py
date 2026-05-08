from core.config.config_manager import ConfigManager
from core.logger.logger_manager import LoggerManager

class BaseSampleBuilder:
    def __init__(self) -> None:
        self.logger = LoggerManager.get_instance().get_logger(self.__class__.__name__)
        self.config_manager = ConfigManager.get_instance()

    EXCLUDED_FEATURES = [
        "match_id", "kickoff_time", "season", "league_id", "league_name", "round",
        "home_team", "home_id", "away_team", "away_id",
        "home_score", "away_score",
        "home_goals_penalty", "away_goals_penalty",
        "home_formation", "away_formation",
        "home_point", "away_point",
    ]
